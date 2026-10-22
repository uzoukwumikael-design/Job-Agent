"""Interactive intake → structured MasterCareer."""

from __future__ import annotations
from app.core.llm import chat, chat_json
from app.models.career import MasterCareer
from app.prompts.intake import SYSTEM, STRUCTURE_PROMPT
async def structure_from_text(user_input: str) -> MasterCareer:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": STRUCTURE_PROMPT.format(user_input=user_input)},
    ]
    data = await chat_json(messages, temperature=0.2)
    career = MasterCareer.model_validate(data)
    return career


async def refine_summary(career: MasterCareer) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                "Write a 3-4 sentence professional summary for an AI Advisor / Consultant "
                "based only on this profile. No invented metrics.\n\n"
                f"{career.model_dump_json(indent=2)}"
            ),
        },
    ]
    return await chat(messages, temperature=0.4)
