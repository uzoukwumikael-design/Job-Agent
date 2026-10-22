# AI Advisor Job Agent

**Hostable web app** for non-technical **AI Advisor / AI Consultant / AI Strategy** roles.

Features:
- **Master career intake** – paste free-form notes → structured profile (never invents facts)
- **Job scoring** – multi-dimension fit (skills, level, domain, location, legitimacy)
- **ATS resume generation** – single-column PDF + DOCX tailored per job
- **Cover letter** drafts grounded in your real experience
- **Application tracker** – stages from saved → offer
- **URL import** for public Greenhouse / Ashby / Lever / company pages

Built for online hosting (FastAPI + simple HTML UI). Human-in-the-loop only — nothing is submitted automatically.

## Quick start (local)

```bash
cd job-agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: PDF rendering
# playwright install   # or rely on WeasyPrint system deps

cp .env.example .env
# Edit .env and set OPENAI_API_KEY (or XAI_API_KEY / compatible)

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000

## Deploy online (any of these)

### Railway / Render / Fly.io
1. Push this repo to GitHub
2. Connect the service, set env vars (`OPENAI_API_KEY`, `APP_SECRET_KEY`, etc.)
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# WeasyPrint system deps (Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Vercel / Cloudflare
Possible with FastAPI adapters; for simplest “normal site” experience prefer Railway/Render/Fly/Docker VPS.

## Target roles (default)

- AI Advisor
- AI Consultant
- AI Strategy Consultant
- AI Transformation Consultant
- Digital Transformation Advisor
- AI Ethics Advisor
- AI Implementation Consultant

Change these during intake or in the generated `data/master/master_career.yaml`.

## Data layout

```
data/
  master/master_career.yaml   # your single source of truth
  jobs/                       # reserved
  tailored/                   # generated PDF, DOCX, cover letters
  tracker/pipeline.json       # application pipeline
```

All data stays on the server you host. No third-party job-search SaaS required.

## Safety rules baked in

- Resume & cover letter prompts forbid inventing metrics, titles, or tools
- Evidence map links JD requirements to your real bullets
- You review and download documents; the agent never auto-applies

## Extending

- Plug JobSpy / Serper / company career APIs into `app/agents/scanner.py`
- Swap tracker to SQLite (`app/models` already prepared)
- Add auth (Authlib / Clerk) for multi-user
- Port the agents into Claude/Codex skill files if you prefer CLI-first later

## License

MIT – use and adapt freely.

## v2 features

- **Multi-user auth** – register / login (JWT cookie), per-user job tracker & STAR bank
- **SQLite** – `data/app.db` for users, jobs, stories
- **Auto-scan** – Greenhouse / Ashby / Lever public APIs for curated companies (OpenAI, Anthropic, McKinsey, BCG, Bain, Accenture, Stripe…) filtered for AI Advisor / Consultant keywords
- Optional **python-jobspy** for LinkedIn/Indeed/Glassdoor (install separately)
- Optional **Serper** API for Google job-link discovery
- **STAR story bank** + **negotiation scripts** on `/interview`
- **Docker Compose** one-command deploy

```bash
cp .env.example .env   # set OPENAI_API_KEY + APP_SECRET_KEY
docker compose up --build
```

Open http://localhost:8000

## v3 features

- **50+ company boards** in `DEFAULT_BOARDS` (AI labs, consulting, fintech, SaaS)
- **Postgres** via `DATABASE_URL` (Docker Compose includes Postgres); SQLite still works by default
- **Per-user master profiles** stored in `user_profiles` table
- **OAuth** Google + LinkedIn (set client IDs/secrets in `.env`)
- **Scheduled scans** with APScheduler (`SCAN_CRON_HOURS=6,18` UTC)
- **Test Tailor Lab** at `/test-tailor` – score + generate resume from any JD without tracking

```bash
# Full stack
cp .env.example .env
docker compose up --build
```

### What more you could add next
- Email alerts when a high-fit job appears
- Chrome extension “Save this job”
- LinkedIn Easy Apply autofill (human-in-the-loop)
- Salary band research per role
- Multi-language resumes
- Team / agency multi-seat accounts

## v4 – research backlog shipped

| Feature | How to use |
|---------|------------|
| **Email / Telegram alerts** | Settings → min score + Telegram chat ID; set `TELEGRAM_BOT_TOKEN` / `RESEND_API_KEY` |
| **Clip bookmarklet** | `/clip` → drag to bookmarks → click on any job page |
| **Salary band estimates** | On a tracked job → **Salary band** |
| **Multi-language resumes** | Settings → preferred language (en/fr/de/es/pt/it/nl) |
| **Form-answer drafts** | On a tracked job → **Form answers** (Why us?, project, fit) |
| **Stronger legitimacy scoring** | Ghost flags surface in score notes; low legitimacy → skip |
| **Team / agency seat** | Settings → create team (label + future shared tracker hook) |

Still natural extensions: full shared team tracker, Chrome MV3 extension package, levels.fyi scrape cache.

## v5 – team tracker, Chrome extension, comp cache, Gemini

### Gemini
```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your-key
```
Uses Google’s OpenAI-compatible endpoint, with optional `google-genai` native client.

### Shared team tracker
1. Settings → Create team (note the team ID)
2. Teammates: Settings → Join team by ID, or open **Team**
3. **Jobs** and **Team** pages show jobs from all members of the same team

### Chrome MV3 extension
```text
chrome-extension/
```
Load unpacked in `chrome://extensions`. See `chrome-extension/README.md`.

### Compensation cache
`data/comp/salary_bands.json` – levels.fyi-style public bands for AI advisor / consultant roles.
Salary agent uses cache first, LLM only as fallback. Edit the JSON to refresh ranges.
