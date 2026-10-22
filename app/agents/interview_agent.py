"""STAR story bank + negotiation scripts for AI Advisor / Consultant roles."""

from __future__ import annotations
import json
from app.core.llm import chat, chat_json
from app.models.career import MasterCareer

STAR_SYSTEM = """You are an expert interview coach for AI Advisor, AI Consultant, and 
management consulting roles. Build STAR stories from REAL experience only. Never invent metrics."""

STAR_PROMPT = """From this master career profile, extract or draft 5–8 reusable STAR stories 
suitable for consulting / AI advisory behavioral interviews.

Themes to cover: leadership, influence without authority, stakeholder management, 
problem-solving, failure/learning, change management, ethics/judgment, driving ROI.

Master profile:
{master_json}

Return JSON:
{{
  "stories": [
    {{
      "title": "short label",
      "themes": ["leadership", "influence"],
      "situation": "2 sentences max",
      "task": "1-2 sentences – what YOU owned",
      "action": "3-6 specific steps, first person I...",
      "result": "quantified outcome if available + learning",
      "reflection": "one line insight"
    }}
  ]
}}
Only use facts present in the profile. If a theme lacks evidence, skip it.
"""

NEGOTIATION_SYSTEM = """You are a compensation negotiation coach for AI Advisor / Consultant roles.
Be practical, market-aware, and professional. Never invent candidate history."""

NEGOTIATION_PROMPT = """Write negotiation scripts for this candidate targeting AI Advisor / Consultant roles.

Profile summary:
{summary}

Target role context (if any): {job_context}

Return JSON:
{{
  "market_framing": "2-3 sentences on how to frame value for AI advisory work",
  "scripts": [
    {{
      "scenario": "When asked current / expected salary early",
      "script": "..."
    }},
    {{
      "scenario": "After verbal offer – counter",
      "script": "..."
    }},
    {{
      "scenario": "Pushing on remote / flexibility",
      "script": "..."
    }},
    {{
      "scenario": "Competing offer leverage",
      "script": "..."
    }}
  ],
  "checklist": ["item1", "item2", "..."]
}}
"""


async def build_star_bank(master: MasterCareer) -> list[dict]:
    messages = [
        {"role": "system", "content": STAR_SYSTEM},
        {"role": "user", "content": STAR_PROMPT.format(master_json=master.model_dump_json(indent=2))},
    ]
    data = await chat_json(messages, temperature=0.3)
    return data.get("stories") or []


async def negotiation_pack(master: MasterCareer, job_context: str = "") -> dict:
    summary = master.professional_summary or master.contact.full_name
    messages = [
        {"role": "system", "content": NEGOTIATION_SYSTEM},
        {
            "role": "user",
            "content": NEGOTIATION_PROMPT.format(summary=summary, job_context=job_context or "General AI Advisor roles"),
        },
    ]
    return await chat_json(messages, temperature=0.4)
