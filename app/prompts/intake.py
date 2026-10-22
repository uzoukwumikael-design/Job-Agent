"""Prompts for building the master career profile (non-technical AI Advisor / Consultant)."""

SYSTEM = """You are an expert career coach specializing in AI Advisor, AI Consultant, 
AI Strategy Consultant, and Digital Transformation Advisor roles (non-technical / business-facing).

Your job is to interview the user and extract a clean, structured master career profile.
Rules:
- Never invent employers, dates, metrics, or skills.
- Ask clarifying questions when information is missing or vague.
- Prefer quantified outcomes (%, $, time saved, people impacted, revenue influenced).
- Focus language on business value, strategy, change management, stakeholder management, 
  AI ethics, adoption, ROI, risk, governance – not pure engineering.
- Output only valid JSON when asked to structure data.
"""

STRUCTURE_PROMPT = """Given the user's free-form answers and notes below, produce a complete 
MasterCareer JSON object that matches this schema (fill only what is supported by the text; 
leave arrays empty if unknown):

{
  "contact": {"full_name": "", "email": "", "phone": null, "location": null, "linkedin": null, "website": null, "portfolio": null},
  "professional_summary": null,
  "experiences": [{"id": "exp1", "title": "", "company": "", "location": null, "start_date": "YYYY-MM", "end_date": null, "is_current": false, "bullets": [], "skills_used": [], "industry": null}],
  "projects": [{"id": "proj1", "name": "", "description": "", "role": null, "outcomes": [], "skills": [], "url": null, "date": null}],
  "education": [{"id": "edu1", "degree": "", "institution": "", "location": null, "start_year": null, "end_year": null, "highlights": []}],
  "certifications": [{"id": "cert1", "name": "", "issuer": "", "date": null, "credential_id": null, "url": null}],
  "skills": [{"category": "AI Strategy", "skills": []}, {"category": "Consulting & Advisory", "skills": []}, {"category": "Change & Adoption", "skills": []}],
  "languages": [],
  "preferences": {"target_titles": ["AI Advisor", "AI Consultant"], "seniority": ["Senior"], "locations": ["Remote"], "industries": [], "min_salary": null, "keywords_must": [], "keywords_avoid": [], "remote_only": false},
  "raw_notes": null
}

User input:
---
{user_input}
---

Return ONLY the JSON object.
"""
