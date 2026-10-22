"""Market salary band estimates – cache first, LLM fallback."""

from __future__ import annotations
from app.core.llm import chat_json
from app.models.job import JobPosting
from app.prompts.tailor import SALARY_SYSTEM, SALARY_PROMPT
from app.services.comp_cache import match_band


async def estimate_salary(job: JobPosting) -> dict:
    cached = match_band(job.title, job.company or "", job.location or "")
    if cached:
        return {
            "currency": cached.get("currency", "USD"),
            "base_low": cached.get("base_low"),
            "base_high": cached.get("base_high"),
            "total_low": cached.get("total_low"),
            "total_high": cached.get("total_high"),
            "notes": (cached.get("notes") or "") + " [from public band cache]",
            "negotiation_levers": ["base", "sign-on", "remote stipend", "title", "equity"],
            "confidence": cached.get("confidence", "medium"),
            "source": "cache",
            "company_type_guess": cached.get("company_type"),
            "level_guess": cached.get("level"),
        }

    messages = [
        {"role": "system", "content": SALARY_SYSTEM},
        {
            "role": "user",
            "content": SALARY_PROMPT.format(
                title=job.title,
                company=job.company,
                location=job.location or "Remote / unspecified",
                description_snippet=(job.description or "")[:2500],
            ),
        },
    ]
    data = await chat_json(messages, temperature=0.2)
    data["source"] = "llm_estimate"
    return data
