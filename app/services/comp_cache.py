"""Cached public compensation bands (levels.fyi-style seed data)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from app.core.config import get_settings


def _cache_path() -> Path:
    p = get_settings().data_path / "comp" / "salary_bands.json"
    if not p.exists():
        # fallback to repo seed
        alt = get_settings().project_root / "data" / "comp" / "salary_bands.json"
        return alt if alt.exists() else p
    return p


def load_bands() -> dict:
    path = _cache_path()
    if not path.exists():
        return {"bands": [], "source": "empty"}
    return json.loads(path.read_text(encoding="utf-8"))


def match_band(
    title: str,
    company: str = "",
    location: str = "",
) -> Optional[dict]:
    """Return best matching cached band or None."""
    data = load_bands()
    title_l = (title or "").lower()
    company_l = (company or "").lower()
    location_l = (location or "").lower()

    # crude company-type hints
    ctype = "enterprise"
    if any(x in company_l for x in ("mckinsey", "bcg", "bain", "quantumblack")):
        ctype = "mbb"
    elif any(x in company_l for x in ("deloitte", "accenture", "pwc", "ey", "kpmg")):
        ctype = "big4"
    elif any(x in company_l for x in ("openai", "anthropic", "deepmind", "google deepmind", "xai")):
        ctype = "ai_lab"
    elif any(x in company_l for x in ("partner",)):
        ctype = "consulting"

    level = "mid"
    if any(x in title_l for x in ("senior", "sr ", "lead", "principal")):
        level = "senior"
    if any(x in title_l for x in ("director", "partner", "head of", "vp ")):
        level = "director"
    if any(x in title_l for x in ("manager",)):
        level = "manager"

    best = None
    best_score = 0
    for band in data.get("bands") or []:
        score = 0
        for pat in band.get("role_patterns") or []:
            if pat in title_l:
                score += 3
        if band.get("level") == level:
            score += 2
        if band.get("company_type") == ctype:
            score += 2
        if location_l and any(
            loc in location_l for loc in (band.get("location") or "").lower().split("/")
        ):
            score += 1
        if score > best_score:
            best_score = score
            best = band
    if best and best_score >= 3:
        out = dict(best)
        out["match_score"] = best_score
        out["source"] = data.get("source", "cache")
        out["currency"] = data.get("currency_default", "USD")
        out["confidence"] = "medium" if best_score >= 5 else "low"
        return out
    return None
