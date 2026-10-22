"""Per-user master career profile (DB) with optional file fallback for single-user."""

from __future__ import annotations
import yaml
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.career import MasterCareer
from app.db import UserProfile


def load_master_for_user(db: Session, user_id: int) -> Optional[MasterCareer]:
    row = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not row or not row.profile_json:
        return None
    return MasterCareer.model_validate(row.profile_json)


def save_master_for_user(db: Session, user_id: int, career: MasterCareer) -> UserProfile:
    row = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    data = career.model_dump(mode="json")
    if row:
        row.profile_json = data
    else:
        row = UserProfile(user_id=user_id, profile_json=data)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def has_master_for_user(db: Session, user_id: int) -> bool:
    row = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return bool(row and row.profile_json)


# Legacy file-based helpers (fallback / migration)
def master_file() -> Path:
    return get_settings().master_path / "master_career.yaml"


def load_master() -> Optional[MasterCareer]:
    path = master_file()
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not data:
        return None
    return MasterCareer.model_validate(data)


def save_master(career: MasterCareer) -> Path:
    path = master_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(career.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def has_master() -> bool:
    return master_file().exists()
