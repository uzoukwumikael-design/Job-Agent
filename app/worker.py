"""Scheduled scan worker – APScheduler inside the app process."""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.db import init_db, get_engine, ScanLog, TrackedJobRow, User, UserProfile
from app.agents.scanner import scan_company_boards
from app.agents.score_agent import score_job
from app.models.career import MasterCareer
from app.models.job import JobPosting

logger = logging.getLogger("worker")
scheduler = AsyncIOScheduler()


async def run_global_scan():
    """Scan boards and attach high-fit jobs to users who have profiles."""
    from sqlalchemy.orm import sessionmaker
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    db = Session()
    log = ScanLog(status="running")
    db.add(log)
    db.commit()
    try:
        found = await scan_company_boards()
        log.jobs_found = len(found)
        added = 0
        users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
        for user in users:
            prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            if not prof or not prof.profile_json:
                continue
            try:
                master = MasterCareer.model_validate(prof.profile_json)
            except Exception:
                continue
            existing = {
                r.url for r in db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id).all()
                if r.url
            }
            for job in found:
                if job.url and job.url in existing:
                    continue
                try:
                    score = await score_job(job, master)
                except Exception:
                    continue
                if score.overall < 3.0:
                    continue
                row = TrackedJobRow(
                    user_id=user.id,
                    job_id=job.id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    url=job.url,
                    source=job.source.value if hasattr(job.source, "value") else str(job.source),
                    description=(job.description or "")[:8000],
                    score_overall=score.overall,
                    score_json=score.model_dump(mode="json"),
                    stage="scored",
                )
                db.add(row)
                added += 1
                if job.url:
                    existing.add(job.url)
            db.commit()
        log.jobs_added = added
        log.status = "ok"
        log.finished_at = datetime.utcnow()
        log.message = f"found={len(found)} added={added}"
        db.commit()
        logger.info("Scheduled scan finished: %s", log.message)
    except Exception as e:
        log.status = "error"
        log.message = str(e)
        log.finished_at = datetime.utcnow()
        db.commit()
        logger.exception("Scheduled scan failed")
    finally:
        db.close()


def start_scheduler():
    settings = get_settings()
    if not settings.enable_scheduler:
        logger.info("Scheduler disabled")
        return
    hours = [int(h.strip()) for h in settings.scan_cron_hours.split(",") if h.strip().isdigit()]
    if not hours:
        hours = [6, 18]
    for h in hours:
        scheduler.add_job(
            lambda: asyncio.create_task(run_global_scan()),
            CronTrigger(hour=h, minute=0),
            id=f"scan_{h}",
            replace_existing=True,
        )
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started for hours UTC: %s", hours)
