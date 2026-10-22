"""
AI Advisor Job Agent v3
Per-user profiles · Postgres/SQLite · OAuth · Scheduled scans · Test-tailor lab
"""

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.db import init_db, get_db, User, TrackedJobRow, StarStory, UserProfile, ScanLog
from app.auth import (
    hash_password, authenticate_user, create_access_token,
    get_user_by_email,
)
from app.services.career_store import (
    load_master_for_user, save_master_for_user, has_master_for_user,
)
from app.agents.intake_agent import structure_from_text, refine_summary
from app.agents.score_agent import score_job
from app.agents.tailor_agent import tailor_resume, generate_cover_letter
from app.agents.scanner import job_from_url, job_from_paste, scan_company_boards, scrape_jobspy
from app.agents.interview_agent import build_star_bank, negotiation_pack
from app.agents.form_agent import draft_form_answers
from app.agents.salary_agent import estimate_salary
from app.services.alerts import notify_high_fit
from app.db import Team, UserProfile
from app.models.job import JobPosting, JobScore
from app.oauth import get_oauth, oauth_enabled
from app.worker import start_scheduler

settings = get_settings()
app = FastAPI(title="AI Advisor Job Agent", version="3.0.0")
app.add_middleware(SessionMiddleware, secret_key=settings.app_secret_key)

static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))


@app.on_event("startup")
def on_startup():
    init_db()
    try:
        start_scheduler()
    except Exception:
        pass


def _user_ctx(request: Request, user: Optional[User]):
    return {"request": request, "user": user, "oauth": oauth_enabled()}


async def html_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    from jose import jwt, JWTError
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        email = payload.get("sub")
        if email:
            return get_user_by_email(db, email)
    except JWTError:
        pass
    return None


def _set_auth_cookie(resp, email: str):
    token = create_access_token(email)
    resp.set_cookie("access_token", token, httponly=True, max_age=60 * 60 * 24 * 7)
    return resp


# ---------- Auth (password + OAuth) ----------

@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request, user=Depends(html_user)):
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("auth.html", {**_user_ctx(request, user), "mode": "register"})


@app.post("/auth/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    db: Session = Depends(get_db),
):
    if get_user_by_email(db, email.lower().strip()):
        return templates.TemplateResponse(
            "auth.html",
            {**_user_ctx(request, None), "mode": "register", "error": "Email already registered"},
            status_code=400,
        )
    u = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        full_name=full_name or None,
    )
    db.add(u)
    db.commit()
    resp = RedirectResponse("/", status_code=303)
    return _set_auth_cookie(resp, u.email)


@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(html_user)):
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse("auth.html", {**_user_ctx(request, user), "mode": "login"})


@app.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    u = authenticate_user(db, email.lower().strip(), password)
    if not u:
        return templates.TemplateResponse(
            "auth.html",
            {**_user_ctx(request, None), "mode": "login", "error": "Invalid email or password"},
            status_code=400,
        )
    resp = RedirectResponse("/", status_code=303)
    return _set_auth_cookie(resp, u.email)


@app.post("/auth/token")
async def token_api(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = authenticate_user(db, form.username.lower().strip(), form.password)
    if not u:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": create_access_token(u.email), "token_type": "bearer"}


@app.get("/auth/logout")
async def logout():
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("access_token")
    return resp


@app.get("/auth/google")
async def google_login(request: Request):
    if not oauth_enabled()["google"]:
        raise HTTPException(400, "Google OAuth not configured")
    oauth = get_oauth()
    redirect_uri = f"{settings.oauth_redirect_base}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    oauth = get_oauth()
    token = await oauth.google.authorize_access_token(request)
    info = token.get("userinfo") or {}
    email = (info.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "No email from Google")
    user = get_user_by_email(db, email)
    if not user:
        user = User(
            email=email,
            full_name=info.get("name"),
            oauth_provider="google",
            oauth_sub=info.get("sub"),
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    resp = RedirectResponse("/", status_code=303)
    return _set_auth_cookie(resp, user.email)


@app.get("/auth/linkedin")
async def linkedin_login(request: Request):
    if not oauth_enabled()["linkedin"]:
        raise HTTPException(400, "LinkedIn OAuth not configured")
    oauth = get_oauth()
    redirect_uri = f"{settings.oauth_redirect_base}/auth/linkedin/callback"
    return await oauth.linkedin.authorize_redirect(request, redirect_uri)


@app.get("/auth/linkedin/callback")
async def linkedin_callback(request: Request, db: Session = Depends(get_db)):
    oauth = get_oauth()
    token = await oauth.linkedin.authorize_access_token(request)
    # LinkedIn OpenID userinfo
    resp = await oauth.linkedin.get("userinfo", token=token)
    info = resp.json()
    email = (info.get("email") or "").lower()
    if not email:
        raise HTTPException(400, "No email from LinkedIn")
    user = get_user_by_email(db, email)
    if not user:
        user = User(
            email=email,
            full_name=info.get("name"),
            oauth_provider="linkedin",
            oauth_sub=info.get("sub"),
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    out = RedirectResponse("/", status_code=303)
    return _set_auth_cookie(out, user.email)


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    master = load_master_for_user(db, user.id) if user else None
    job_count = db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id).count() if user else 0
    return templates.TemplateResponse(
        "index.html",
        {
            **_user_ctx(request, user),
            "has_master": master is not None,
            "master_name": master.contact.full_name if master else None,
            "tracker_count": job_count,
            "target_titles": (master.preferences.target_titles if master else [
                "AI Advisor", "AI Consultant", "AI Strategy Consultant"
            ]),
        },
    )


@app.get("/intake", response_class=HTMLResponse)
async def intake_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    master = load_master_for_user(db, user.id) if user else None
    return templates.TemplateResponse("intake.html", {**_user_ctx(request, user), "master": master})


@app.post("/intake")
async def intake_submit(
    request: Request,
    raw_notes: str = Form(...),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    if not raw_notes.strip():
        raise HTTPException(400, "Please provide career information.")
    try:
        career = await structure_from_text(raw_notes)
        if not career.professional_summary:
            career.professional_summary = await refine_summary(career)
        save_master_for_user(db, user.id, career)
        return RedirectResponse("/profile", status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "intake.html",
            {**_user_ctx(request, user), "error": str(e), "raw_notes": raw_notes},
            status_code=400,
        )


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    return templates.TemplateResponse("profile.html", {**_user_ctx(request, user), "master": master})


@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    rows = _jobs_for_user(db, user, include_team=True)
    return templates.TemplateResponse("jobs.html", {**_user_ctx(request, user), "jobs": rows, "master": master, "team_shared": bool(user.team_id)})




def _jobs_for_user(db: Session, user: User, include_team: bool = True):
    """Jobs owned by user, or by any member of the same team (shared tracker)."""
    q = db.query(TrackedJobRow)
    if include_team and user.team_id:
        member_ids = [u.id for u in db.query(User).filter(User.team_id == user.team_id).all()]
        if not member_ids:
            member_ids = [user.id]
        return q.filter(TrackedJobRow.user_id.in_(member_ids)).order_by(TrackedJobRow.updated_at.desc()).all()
    return q.filter(TrackedJobRow.user_id == user.id).order_by(TrackedJobRow.updated_at.desc()).all()

async def _maybe_alert(user: User, job: JobPosting, score: JobScore):
    try:
        min_s = user.alert_min_score if user.alert_min_score is not None else 4.0
        if score.overall >= min_s:
            await notify_high_fit(
                user_email=user.email,
                telegram_chat_id=user.telegram_chat_id if user.alerts_telegram else None,
                title=job.title,
                company=job.company,
                score=score.overall,
                url=job.url or "",
                min_score=min_s,
            )
    except Exception:
        pass

def _save_job_row(db: Session, user: User, job: JobPosting, score: JobScore) -> TrackedJobRow:
    row = TrackedJobRow(
        user_id=user.id,
        job_id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        url=job.url,
        source=job.source.value if hasattr(job.source, "value") else str(job.source),
        description=job.description[:8000],
        score_overall=score.overall,
        score_json=score.model_dump(mode="json"),
        stage="scored",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post("/jobs/add")
async def add_job(
    request: Request,
    title: str = Form(...),
    company: str = Form(...),
    description: str = Form(...),
    location: str = Form(""),
    url: str = Form(""),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    job = job_from_paste(title, company, description, location or None, url)
    score = await score_job(job, master)
    _save_job_row(db, user, job, score)
    await _maybe_alert(user, job, score)
    return RedirectResponse("/jobs", status_code=303)


@app.post("/jobs/from-url")
async def add_job_url(
    request: Request,
    url: str = Form(...),
    title: str = Form(""),
    company: str = Form(""),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    try:
        job = await job_from_url(url, title, company)
        score = await score_job(job, master)
        _save_job_row(db, user, job, score)
        await _maybe_alert(user, job, score)
    except Exception as e:
        rows = db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id).all()
        return templates.TemplateResponse(
            "jobs.html",
            {**_user_ctx(request, user), "jobs": rows, "master": master, "error": str(e)},
            status_code=400,
        )
    return RedirectResponse("/jobs", status_code=303)


@app.post("/jobs/scan")
async def scan_jobs(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    keywords = master.preferences.target_titles + master.preferences.keywords_must
    found = await scan_company_boards(keywords=[k.lower() for k in keywords] or None)
    js = scrape_jobspy(
        search_term=master.preferences.target_titles[0] if master.preferences.target_titles else "AI Consultant",
        location="Remote",
        results_wanted=15,
    )
    found.extend(js)
    added = 0
    existing_urls = {r.url for r in db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id).all() if r.url}
    for job in found[:50]:
        if job.url and job.url in existing_urls:
            continue
        score = await score_job(job, master)
        if score.overall >= 2.5:
            _save_job_row(db, user, job, score)
            await _maybe_alert(user, job, score)
            added += 1
            if job.url:
                existing_urls.add(job.url)
    return RedirectResponse(f"/jobs?scanned={added}", status_code=303)


@app.post("/jobs/{job_id}/tailor")
async def tailor_job(job_id: str, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        raise HTTPException(400, "No master profile")
    row = db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id, TrackedJobRow.job_id == job_id).first()
    if not row:
        raise HTTPException(404, "Job not found")
    job = JobPosting(
        id=row.job_id, title=row.title, company=row.company, location=row.location,
        url=row.url or "", source=row.source, description=row.description or "",
    )
    score = JobScore.model_validate(row.score_json) if row.score_json else None
    prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    lang = (prof.preferred_language if prof and prof.preferred_language else "en")
    result = await tailor_resume(job, master, score, language=lang)
    cover = await generate_cover_letter(job, master, result["content"], language=lang)
    row.tailored_pdf = result["paths"].get("pdf")
    row.tailored_docx = result["paths"].get("docx")
    cover_path = settings.tailored_path / f"{user.id}_{job_id}_cover.txt"
    cover_path.write_text(cover, encoding="utf-8")
    row.cover_path = str(cover_path.relative_to(settings.project_root))
    row.stage = "tailored"
    row.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/jobs", status_code=303)


@app.post("/jobs/{row_id}/stage")
async def update_stage(
    row_id: int, stage: str = Form(...),
    user: Optional[User] = Depends(html_user), db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    row = db.query(TrackedJobRow).filter(TrackedJobRow.id == row_id, TrackedJobRow.user_id == user.id).first()
    if row:
        row.stage = stage
        row.updated_at = datetime.utcnow()
        if stage == "applied":
            row.applied_at = datetime.utcnow()
        db.commit()
    return RedirectResponse("/jobs", status_code=303)


# ---------- Test Tailor Lab (strengths test without full pipeline) ----------

@app.get("/test-tailor", response_class=HTMLResponse)
async def test_tailor_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    master = load_master_for_user(db, user.id) if user else None
    return templates.TemplateResponse(
        "test_tailor.html",
        {**_user_ctx(request, user), "master": master, "result": None},
    )


@app.post("/test-tailor")
async def test_tailor_run(
    request: Request,
    job_title: str = Form(...),
    company: str = Form(...),
    description: str = Form(...),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    job = job_from_paste(job_title, company, description)
    score = await score_job(job, master)
    tailored = await tailor_resume(job, master, score)
    cover = await generate_cover_letter(job, master, tailored["content"])
    result = {
        "score": score.model_dump(mode="json"),
        "content": tailored["content"],
        "paths": tailored["paths"],
        "cover": cover,
        "job": {"title": job.title, "company": job.company, "id": job.id},
    }
    return templates.TemplateResponse(
        "test_tailor.html",
        {**_user_ctx(request, user), "master": master, "result": result},
    )


# ---------- Interview ----------

@app.get("/interview", response_class=HTMLResponse)
async def interview_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    master = load_master_for_user(db, user.id) if user else None
    stories = db.query(StarStory).filter(StarStory.user_id == user.id).all() if user else []
    return templates.TemplateResponse(
        "interview.html",
        {**_user_ctx(request, user), "master": master, "stories": stories, "negotiation": None},
    )


@app.post("/interview/star")
async def generate_star(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    stories = await build_star_bank(master)
    db.query(StarStory).filter(StarStory.user_id == user.id).delete()
    for s in stories:
        db.add(StarStory(
            user_id=user.id,
            title=s.get("title", "Story"),
            themes=s.get("themes") or [],
            situation=s.get("situation", ""),
            task=s.get("task", ""),
            action=s.get("action", ""),
            result=s.get("result", ""),
            reflection=s.get("reflection", ""),
        ))
    db.commit()
    return RedirectResponse("/interview", status_code=303)


@app.post("/interview/negotiate")
async def generate_negotiate(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    pack = await negotiation_pack(master)
    stories = db.query(StarStory).filter(StarStory.user_id == user.id).all()
    return templates.TemplateResponse(
        "interview.html",
        {**_user_ctx(request, user), "master": master, "stories": stories, "negotiation": pack},
    )


@app.get("/download/{path:path}")
async def download_file(path: str):
    full = settings.project_root / path
    if not full.exists() or not str(full.resolve()).startswith(str(settings.project_root.resolve())):
        raise HTTPException(404)
    return FileResponse(full, filename=full.name)




# ---------- Settings / Alerts / Language ----------

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return templates.TemplateResponse(
        "settings.html",
        {
            **_user_ctx(request, user),
            "preferred_language": (prof.preferred_language if prof else "en"),
        },
    )


@app.post("/settings")
async def settings_save(
    request: Request,
    alert_min_score: float = Form(4.0),
    telegram_chat_id: str = Form(""),
    alerts_email: Optional[str] = Form(None),
    alerts_telegram: Optional[str] = Form(None),
    preferred_language: str = Form("en"),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    user.alert_min_score = float(alert_min_score)
    user.telegram_chat_id = telegram_chat_id.strip() or None
    user.alerts_email = alerts_email is not None
    user.alerts_telegram = alerts_telegram is not None
    prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if prof:
        prof.preferred_language = preferred_language.strip() or "en"
    elif preferred_language:
        # create empty profile shell if needed
        pass
    db.commit()
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/jobs/{job_id}/form-answers")
async def job_form_answers(job_id: str, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    row = db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id, TrackedJobRow.job_id == job_id).first()
    if not master or not row:
        raise HTTPException(404)
    job = JobPosting(id=row.job_id, title=row.title, company=row.company, location=row.location,
                     url=row.url or "", source=row.source, description=row.description or "")
    answers = await draft_form_answers(job, master)
    row.form_answers_json = answers
    row.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/jobs", status_code=303)


@app.post("/jobs/{job_id}/salary")
async def job_salary(job_id: str, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    row = db.query(TrackedJobRow).filter(TrackedJobRow.user_id == user.id, TrackedJobRow.job_id == job_id).first()
    if not row:
        raise HTTPException(404)
    job = JobPosting(id=row.job_id, title=row.title, company=row.company, location=row.location,
                     url=row.url or "", source=row.source, description=row.description or "")
    band = await estimate_salary(job)
    row.salary_json = band
    row.updated_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/jobs", status_code=303)


@app.get("/clip", response_class=HTMLResponse)
async def clip_page(request: Request, user: Optional[User] = Depends(html_user)):
    base = settings.oauth_redirect_base.rstrip("/")
    bookmarklet = (
        "javascript:(function(){var t=document.title||'';var u=location.href;"
        "var d=(document.body&&document.body.innerText||'').slice(0,8000);"
        f"window.open('{base}/jobs/clip?title='+encodeURIComponent(t)"
        "+'&url='+encodeURIComponent(u)+'&description='+encodeURIComponent(d),'_blank');})();"
    )
    return templates.TemplateResponse("clip.html", {**_user_ctx(request, user), "bookmarklet": bookmarklet})


@app.get("/jobs/clip", response_class=HTMLResponse)
async def clip_import_get(
    request: Request,
    title: str = "",
    url: str = "",
    description: str = "",
    user: Optional[User] = Depends(html_user),
):
    return templates.TemplateResponse(
        "clip_import.html",
        {**_user_ctx(request, user), "title": title, "url": url, "description": description[:8000]},
    )


@app.post("/jobs/clip")
async def clip_import_post(
    request: Request,
    title: str = Form(...),
    company: str = Form("Unknown"),
    description: str = Form(...),
    url: str = Form(""),
    location: str = Form(""),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    master = load_master_for_user(db, user.id)
    if not master:
        return RedirectResponse("/intake")
    job = job_from_paste(title, company, description, location or None, url)
    score = await score_job(job, master)
    _save_job_row(db, user, job, score)
    await _maybe_alert(user, job, score)
    return RedirectResponse("/jobs", status_code=303)


@app.post("/team/create")
async def team_create(
    name: str = Form(...),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    team = Team(name=name.strip(), owner_user_id=user.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    user.team_id = team.id
    db.commit()
    return RedirectResponse("/settings?team=1", status_code=303)





@app.post("/team/join")
async def team_join(
    team_id: int = Form(...),
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(404, "Team not found")
    user.team_id = team.id
    db.commit()
    return RedirectResponse("/settings?team=joined", status_code=303)


@app.post("/team/leave")
async def team_leave(
    user: Optional[User] = Depends(html_user),
    db: Session = Depends(get_db),
):
    if not user:
        return RedirectResponse("/auth/login")
    user.team_id = None
    db.commit()
    return RedirectResponse("/settings?team=left", status_code=303)


@app.get("/team", response_class=HTMLResponse)
async def team_page(request: Request, user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        return RedirectResponse("/auth/login")
    team = db.query(Team).filter(Team.id == user.team_id).first() if user.team_id else None
    members = []
    shared_jobs = []
    if team:
        members = db.query(User).filter(User.team_id == team.id).all()
        shared_jobs = _jobs_for_user(db, user, include_team=True)
    return templates.TemplateResponse(
        "team.html",
        {**_user_ctx(request, user), "team": team, "members": members, "shared_jobs": shared_jobs},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/admin/scan-logs")
async def scan_logs(user: Optional[User] = Depends(html_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(401)
    logs = db.query(ScanLog).order_by(ScanLog.started_at.desc()).limit(20).all()
    return [{"id": l.id, "status": l.status, "found": l.jobs_found, "added": l.jobs_added, "msg": l.message, "at": str(l.started_at)} for l in logs]
