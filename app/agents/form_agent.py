"""Draft answers for open-ended ATS application questions."""

from __future__ import annotations
from app.core.llm import chat_json
from app.models.career import MasterCareer
from app.models.job import JobPosting
from app.prompts.tailor import FORM_ANSWERS_SYSTEM, FORM_ANSWERS_PROMPT


async def draft_form_answers(job: JobPosting, master: MasterCareer) -> list[dict]:
    messages = [
        {"role": "system", "content": FORM_ANSWERS_SYSTEM},
        {
            "role": "user",
            "content": FORM_ANSWERS_PROMPT.format(
                title=job.title,
                company=job.company,
                description_snippet=(job.description or "")[:2000],
                master_json=master.model_dump_json(indent=2),
            ),
        },
    ]
    data = await chat_json(messages, temperature=0.3)
    return data.get("answers") or []
