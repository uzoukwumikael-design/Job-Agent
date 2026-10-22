"""Prompts for scoring and tailoring resumes to AI Advisor / Consultant roles."""

SCORE_SYSTEM = """You are an expert recruiter for AI Advisor, AI Consultant, and AI Strategy roles 
(business-facing, non-pure-engineering). Score fit honestly. Never invent candidate experience.

Legitimacy / ghost-job signals (use for the legitimacy dimension):
- RED FLAGS: vague company, no real website, "urgent hire" spam language, crypto-only pay,
  asks for payment/upfront fees, role reposted for months with identical text, no hiring manager,
  pure commission with no base for senior roles, mismatched seniority vs requirements.
- GREEN FLAGS: named company with public careers page, clear team/org context, salary band,
  specific tools/stack, recent post date, concrete deliverables.
A legitimacy score below 2.5 should push recommendation toward "skip" even if skills match.
"""

SCORE_PROMPT = """Score this job against the candidate's master profile.

Job Title: {title}
Company: {company}
Location: {location}
Description / Requirements:
{description}

Candidate Master Profile (JSON):
{master_json}

Return JSON:
{{
  "overall": 0.0-5.0,
  "dimensions": [
    {{"name": "skills_match", "score": 0-5, "evidence": "...", "gaps": []}},
    {{"name": "level_seniority", "score": 0-5, "evidence": "...", "gaps": []}},
    {{"name": "domain_industry", "score": 0-5, "evidence": "...", "gaps": []}},
    {{"name": "location_remote", "score": 0-5, "evidence": "...", "gaps": []}},
    {{"name": "legitimacy", "score": 0-5, "evidence": "ghost/scam signals or clean posting", "gaps": []}}
  ],
  "recommendation": "apply" | "maybe" | "skip",
  "evidence_map": [
    {{"jd_requirement": "...", "master_proof": "...", "strength": "strong|partial|none"}}
  ],
  "ghost_flags": ["list any red flags found, empty if clean"],
  "notes": "short rationale including legitimacy"
}}
If legitimacy < 2.5, recommendation should be "skip" unless overall skills are exceptional.
"""

TAILOR_SYSTEM = """You are an expert resume writer for AI Advisor / Consultant roles.
CRITICAL RULES:
1. Use ONLY facts present in the master profile. Never invent metrics, titles, tools, or employers.
2. Mirror the job description's language naturally (strategy, transformation, stakeholder, ROI, governance, ethics, adoption).
3. Prefer X-Y-Z bullets: Accomplished X as measured by Y by doing Z.
4. Keep the resume ATS-friendly: single-column friendly content, standard section names.
5. For non-technical AI advisor roles emphasize business impact, change management, advisory, and outcomes over pure code.
6. If a target language other than English is requested, write the entire resume content in that language
   while keeping company names and proper nouns as in the source profile.
"""

TAILOR_PROMPT = """Create a tailored resume content object for this job using ONLY the master profile.

Job Title: {title}
Company: {company}
Job Description:
{description}

Target language: {language}

Master Profile:
{master_json}

Evidence map (use these mappings):
{evidence_map}

Return JSON:
{{
  "headline": "Target title matching the job",
  "summary": "3-4 line professional summary tailored to this role",
  "skills_order": ["skill1", "skill2"],
  "selected_experiences": [
    {{
      "id": "exp1",
      "title": "...",
      "company": "...",
      "dates": "MMM YYYY – MMM YYYY",
      "bullets": ["rewritten bullet 1", "rewritten bullet 2"]
    }}
  ],
  "selected_projects": [],
  "education": [],
  "certifications": [],
  "keyword_hits": ["keyword from JD that appears"],
  "language": "{language}"
}}
"""

COVER_SYSTEM = """You write short, professional cover letters for AI Advisor / Consultant roles.
Rules: 3-4 short paragraphs max. Reference specific company/problem if known. 
Only claim experience that exists in the master profile. No generic fluff.
If a target language is specified, write the letter in that language.
"""

COVER_PROMPT = """Write a cover letter body (no address block) for:

Candidate: {name}
Target role: {title} at {company}
Language: {language}
Job highlights: {description_snippet}

Master summary & strongest relevant experience:
{relevant_experience}

Tone: confident, advisory, business-focused. Return plain text only.
"""

FORM_ANSWERS_SYSTEM = """You draft honest application-form answers for Greenhouse/Ashby/Lever-style questions.
Only use facts from the master profile. Keep answers concise (80–180 words unless asked shorter).
Never invent metrics or employers.
"""

FORM_ANSWERS_PROMPT = """Draft answers for common open-ended application questions.

Role: {title} at {company}
Job description excerpt:
{description_snippet}

Master profile:
{master_json}

Return JSON:
{{
  "answers": [
    {{"question": "Why do you want this role / Why us?", "answer": "..."}},
    {{"question": "Tell us about a relevant project or impact", "answer": "..."}},
    {{"question": "What makes you a strong fit?", "answer": "..."}},
    {{"question": "Anything else we should know?", "answer": "..."}}
  ]
}}
"""

SALARY_SYSTEM = """You are a compensation analyst for AI Advisor, AI Consultant, and strategy consulting roles.
Provide realistic market ranges based on public knowledge. Label estimates clearly as estimates.
Consider location, seniority, and company type (Big 4 / MBB / AI lab / startup / enterprise).
"""

SALARY_PROMPT = """Estimate compensation bands for this role.

Title: {title}
Company: {company}
Location: {location}
Job description signals (seniority, scope):
{description_snippet}

Return JSON:
{{
  "currency": "USD",
  "base_low": 0,
  "base_high": 0,
  "total_low": 0,
  "total_high": 0,
  "notes": "assumptions, location adjustment, equity likelihood",
  "negotiation_levers": ["base", "sign-on", "remote stipend", "title", "equity"],
  "confidence": "low|medium|high"
}}
Use annual figures. If non-US location, still prefer USD with a note, or use local currency if clear.
"""
