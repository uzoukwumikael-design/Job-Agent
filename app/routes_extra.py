"""Extra routes: settings/alerts, form answers, salary, teams, bookmarklet API."""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.db import get_db, User, TrackedJobRow, Team, UserProfile
from app.services.career_store import load_master_for_user
from app.agents.form_agent import draft_form_answers
from app.agents.salary_agent import estimate_salary
from app.agents.score_agent import score_job
from app.agents.scanner import job_from_paste
from app.models.job import JobPosting, JobScore
from app.services.alerts import notify_high_fit
from app.core.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
settings = get_settings()


def _ctx(request, user, **kw):
    from app.oauth import oauth_enabled
    return {"request": request, "user": user, "oauth": oauth_enabled(), **kw}


# ---------- Settings / Alerts ----------

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: Optional[User] = None, db: Session = Depends(get_db)):
    # user injected by dependency in main – this is included after html_user pattern
    return templates.TemplateResponse("settings.html", _ctx(request, user))


@router.post("/settings")
async def settings_save(
    request: Request,
    alert_min_score: float = Form(4.0),
    telegram_chat_id: str = Form(""),
    alerts_email: str = Form(""),
    alerts_telegram: str = Form(""),
    preferred_language: str = Form("en"),
    db: Session = Depends(get_db),
):
    # caller must pass user via form session – handled in main wiring
    raise HTTPException(501, "Wired via main")


# ---------- Form answers + salary for a tracked job ----------

@router.post("/jobs/{job_id}/form-answers")
async def job_form_answers(job_id: str, db: Session = Depends(get_db)):
    raise HTTPException(501, "Wired via main")


@router.post("/jobs/{job_id}/salary")
async def job_salary(job_id: str, db: Session = Depends(get_db)):
    raise HTTPException(501, "Wired via main")


# ---------- Bookmarklet / clip API ----------

@router.get("/clip", response_class=HTMLResponse)
async def clip_page(request: Request):
    base = settings.oauth_redirect_base.rstrip("/")
    bookmarklet = (
        "javascript:(function(){"
        "var t=document.title||'';"
        "var u=location.href;"
        "var d=(document.body&&document.body.innerText||'').slice(0,12000);"
        f"window.open('{base}/jobs/clip?title='+encodeURIComponent(t)"
        "+'&url='+encodeURIComponent(u)"
        "+'&description='+encodeURIComponent(d.slice(0,8000)),'_blank');"
        "})();"
    )
    return templates.TemplateResponse(
        "clip.html",
        {"request": request, "bookmarklet": bookmarklet, "user": None, "oauth": {}},
    )


@router.get("/jobs/clip", response_class=HTMLResponse)
async def clip_import(
    request: Request,
    title: str = "",
    url: str = "",
    description: str = "",
    db: Session = Depends(get_db),
):
    """Landing page after bookmarklet – user must be logged in to save."""
    return templates.TemplateResponse(
        "clip_import.html",
        {
            "request": request,
            "title": title,
            "url": url,
            "description": description[:8000],
            "user": None,
            "oauth": {},
        },
    )
