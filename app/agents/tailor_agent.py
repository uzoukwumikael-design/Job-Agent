"""Tailor resume + cover letter from master + scored job (multi-language)."""

from __future__ import annotations
import json
from app.core.llm import chat, chat_json
from app.models.career import MasterCareer
from app.models.job import JobPosting, JobScore
from app.prompts.tailor import TAILOR_SYSTEM, TAILOR_PROMPT, COVER_SYSTEM, COVER_PROMPT
from app.services.resume_generator import generate_documents
from app.core.config import get_settings


async def tailor_resume(
    job: JobPosting,
    master: MasterCareer,
    score: JobScore | None = None,
    language: str = "en",
) -> dict:
    evidence = json.dumps(score.evidence_map if score else [], indent=2)
    messages = [
        {"role": "system", "content": TAILOR_SYSTEM},
        {
            "role": "user",
            "content": TAILOR_PROMPT.format(
                title=job.title,
                company=job.company,
                description=job.description[:8000],
                master_json=master.model_dump_json(indent=2),
                evidence_map=evidence,
                language=language or "en",
            ),
        },
    ]
    tailored = await chat_json(messages, temperature=0.25)
    paths = generate_documents(master, tailored, job.id, job.company)
    return {"content": tailored, "paths": paths}


async def generate_cover_letter(
    job: JobPosting,
    master: MasterCareer,
    tailored: dict,
    language: str = "en",
) -> str:
    relevant = tailored.get("summary", "") + "\n"
    for exp in tailored.get("selected_experiences", [])[:2]:
        relevant += f"\n{exp.get('title')} at {exp.get('company')}:\n"
        relevant += "\n".join(f"- {b}" for b in exp.get("bullets", [])[:3])

    messages = [
        {"role": "system", "content": COVER_SYSTEM},
        {
            "role": "user",
            "content": COVER_PROMPT.format(
                name=master.contact.full_name,
                title=job.title,
                company=job.company,
                language=language or "en",
                description_snippet=job.description[:1500],
                relevant_experience=relevant,
            ),
        },
    ]
    body = await chat(messages, temperature=0.4)
    settings = get_settings()
    safe = "".join(c if c.isalnum() else "_" for c in job.company)[:30]
    path = settings.tailored_path / f"{job.id}_{safe}_cover.txt"
    path.write_text(body, encoding="utf-8")
    return body
