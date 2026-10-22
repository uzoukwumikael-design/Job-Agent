"""Database – SQLite by default, Postgres when DATABASE_URL is set."""

from __future__ import annotations
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

from app.core.config import get_settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    oauth_provider = Column(String(32), nullable=True)
    oauth_sub = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    # Alerts
    alert_min_score = Column(Float, default=4.0)
    telegram_chat_id = Column(String(64), nullable=True)
    alerts_email = Column(Boolean, default=True)
    alerts_telegram = Column(Boolean, default=False)
    # Team
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    jobs = relationship("TrackedJobRow", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("StarStory", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    team = relationship("Team", back_populates="members")


class Team(Base):
    """Lightweight agency / multi-seat support."""
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship("User", back_populates="team")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    profile_json = Column(JSON, nullable=False, default=dict)
    preferred_language = Column(String(16), default="en")  # en, fr, de, es, pt, ...
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="profile")


class TrackedJobRow(Base):
    __tablename__ = "tracked_jobs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String(64), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    url = Column(Text, nullable=True)
    source = Column(String(64), default="manual")
    description = Column(Text, default="")
    score_overall = Column(Float, nullable=True)
    score_json = Column(JSON, nullable=True)
    stage = Column(String(32), default="saved")
    tailored_pdf = Column(String(512), nullable=True)
    tailored_docx = Column(String(512), nullable=True)
    cover_path = Column(String(512), nullable=True)
    form_answers_json = Column(JSON, nullable=True)
    salary_json = Column(JSON, nullable=True)
    notes = Column(Text, default="")
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="jobs")
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)


class StarStory(Base):
    __tablename__ = "star_stories"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    themes = Column(JSON, default=list)
    situation = Column(Text, default="")
    task = Column(Text, default="")
    action = Column(Text, default="")
    result = Column(Text, default="")
    reflection = Column(Text, default="")
    source_job_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="stories")


class ScanLog(Base):
    __tablename__ = "scan_logs"
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    jobs_found = Column(Integer, default=0)
    jobs_added = Column(Integer, default=0)
    status = Column(String(32), default="running")
    message = Column(Text, default="")


_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        url = settings.database_url
        if url.startswith("sqlite"):
            _engine = create_engine(url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    get_engine()
