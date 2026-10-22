"""Score a job against master profile (with legitimacy / ghost detection)."""

from __future__ import annotations
from app.core.llm import chat_json
from app.models.career import MasterCareer
from app.models.job import JobPosting, JobScore, FitDimension
from app.prompts.tailor import SCORE_SYSTEM, SCORE_PROMPT


async def score_job(job: JobPosting, master: MasterCareer) -> JobScore:
    messages = [
        {"role": "system", "content": SCORE_SYSTEM},
        {
            "role": "user",
            "content": SCORE_PROMPT.format(
                title=job.title,
                company=job.company,
                location=job.location or "Not specified",
                description=job.description[:8000],
                master_json=master.model_dump_json(indent=2),
            ),
        },
    ]
    data = await chat_json(messages, temperature=0.2)
    dimensions = [FitDimension(**d) for d in data.get("dimensions", [])]
    notes = data.get("notes") or ""
    flags = data.get("ghost_flags") or []
    if flags:
        notes = (notes + " | Flags: " + "; ".join(flags)).strip(" |")
    return JobScore(
        job_id=job.id,
        overall=float(data.get("overall", 0)),
        dimensions=dimensions,
        recommendation=data.get("recommendation", "maybe"),
        evidence_map=data.get("evidence_map", []),
        notes=notes,
    )
