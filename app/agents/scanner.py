"""Stronger job discovery:
- Manual paste / single URL
- JobSpy (optional)
- Direct Greenhouse / Ashby / Lever public board APIs
- Optional Serper Google search
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List
from bs4 import BeautifulSoup
import httpx

from app.models.job import JobPosting, JobSource
from app.core.config import get_settings

# Expanded curated boards – AI labs, consulting, fintech, SaaS (public APIs)
DEFAULT_BOARDS = [
    # AI / research labs
    {"name": "OpenAI", "ats": "ashby", "slug": "openai"},
    {"name": "Anthropic", "ats": "ashby", "slug": "anthropic"},
    {"name": "Perplexity", "ats": "ashby", "slug": "perplexity-ai"},
    {"name": "Hugging Face", "ats": "greenhouse", "slug": "huggingface"},
    {"name": "Scale AI", "ats": "greenhouse", "slug": "scaleai"},
    {"name": "Cohere", "ats": "ashby", "slug": "cohere"},
    {"name": "Adept", "ats": "ashby", "slug": "adept"},
    {"name": "Inflection", "ats": "ashby", "slug": "inflection"},
    {"name": "Character.AI", "ats": "ashby", "slug": "character"},
    {"name": "ElevenLabs", "ats": "ashby", "slug": "elevenlabs"},
    {"name": "Mistral", "ats": "ashby", "slug": "mistral"},
    {"name": "Together AI", "ats": "ashby", "slug": "togetherai"},
    # Big tech
    {"name": "Google", "ats": "greenhouse", "slug": "google"},
    {"name": "Microsoft", "ats": "greenhouse", "slug": "microsoft"},
    {"name": "Meta", "ats": "greenhouse", "slug": "meta"},
    {"name": "Amazon", "ats": "greenhouse", "slug": "amazon"},
    {"name": "Apple", "ats": "greenhouse", "slug": "apple"},
    {"name": "NVIDIA", "ats": "greenhouse", "slug": "nvidia"},
    # Consulting / advisory (often Greenhouse)
    {"name": "McKinsey", "ats": "greenhouse", "slug": "mckinsey"},
    {"name": "BCG", "ats": "greenhouse", "slug": "bcg"},
    {"name": "Bain", "ats": "greenhouse", "slug": "bain"},
    {"name": "Accenture", "ats": "greenhouse", "slug": "accenture"},
    {"name": "Deloitte", "ats": "greenhouse", "slug": "deloitte"},
    {"name": "PwC", "ats": "greenhouse", "slug": "pwc"},
    {"name": "EY", "ats": "greenhouse", "slug": "ey"},
    {"name": "KPMG", "ats": "greenhouse", "slug": "kpmg"},
    {"name": "Oliver Wyman", "ats": "greenhouse", "slug": "oliverwyman"},
    {"name": "Roland Berger", "ats": "greenhouse", "slug": "rolandberger"},
    # Fintech / SaaS
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Notion", "ats": "ashby", "slug": "notion"},
    {"name": "Ramp", "ats": "ashby", "slug": "ramp"},
    {"name": "Brex", "ats": "greenhouse", "slug": "brex"},
    {"name": "Plaid", "ats": "greenhouse", "slug": "plaid"},
    {"name": "Coinbase", "ats": "greenhouse", "slug": "coinbase"},
    {"name": "Robinhood", "ats": "greenhouse", "slug": "robinhood"},
    {"name": "Rippling", "ats": "greenhouse", "slug": "rippling"},
    {"name": "Gusto", "ats": "greenhouse", "slug": "gusto"},
    {"name": "Mercury", "ats": "ashby", "slug": "mercury"},
    {"name": "Datadog", "ats": "greenhouse", "slug": "datadog"},
    {"name": "Cloudflare", "ats": "greenhouse", "slug": "cloudflare"},
    {"name": "Figma", "ats": "greenhouse", "slug": "figma"},
    {"name": "Linear", "ats": "ashby", "slug": "linear"},
    {"name": "Vercel", "ats": "ashby", "slug": "vercel"},
    {"name": "Retool", "ats": "ashby", "slug": "retool"},
    {"name": "Airtable", "ats": "greenhouse", "slug": "airtable"},
    {"name": "Asana", "ats": "greenhouse", "slug": "asana"},
    {"name": "Canva", "ats": "greenhouse", "slug": "canva"},
    {"name": "Shopify", "ats": "greenhouse", "slug": "shopify"},
    {"name": "Airbnb", "ats": "greenhouse", "slug": "airbnb"},
    {"name": "Uber", "ats": "greenhouse", "slug": "uber"},
    {"name": "DoorDash", "ats": "greenhouse", "slug": "doordash"},
    {"name": "Lyft", "ats": "greenhouse", "slug": "lyft"},
    {"name": "Instacart", "ats": "greenhouse", "slug": "instacart"},
    # More AI-adjacent
    {"name": "Palantir", "ats": "lever", "slug": "palantir"},
    {"name": "Anduril", "ats": "ashby", "slug": "anduril"},
    {"name": "C3.ai", "ats": "greenhouse", "slug": "c3ai"},
    {"name": "DataRobot", "ats": "greenhouse", "slug": "datarobot"},
    {"name": "UiPath", "ats": "greenhouse", "slug": "uipath"},
]


async def fetch_url_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 JobAgent/1.0"})
        r.raise_for_status()
        return r.text


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines() if ln.strip()]
    return "\n".join(lines)


async def job_from_url(url: str, title_hint: str = "", company_hint: str = "") -> JobPosting:
    html = await fetch_url_text(url)
    text = _clean_text(html)
    title = title_hint or (text.split("\n")[0][:120] if text else "Unknown Role")
    company = company_hint or "Unknown"
    source = JobSource.other
    if "greenhouse" in url:
        source = JobSource.greenhouse
    elif "ashbyhq" in url:
        source = JobSource.ashby
    elif "lever.co" in url:
        source = JobSource.lever
    return JobPosting(
        id=str(uuid.uuid4())[:8],
        title=title,
        company=company,
        url=url,
        source=source,
        description=text[:12000],
        scraped_at=datetime.utcnow(),
    )


def job_from_paste(
    title: str, company: str, description: str,
    location: Optional[str] = None, url: str = "",
) -> JobPosting:
    return JobPosting(
        id=str(uuid.uuid4())[:8],
        title=title.strip(),
        company=company.strip(),
        location=location,
        url=url or f"manual://{uuid.uuid4().hex[:6]}",
        source=JobSource.manual,
        description=description.strip(),
        scraped_at=datetime.utcnow(),
    )


async def fetch_greenhouse(slug: str, company_name: str) -> List[JobPosting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    jobs: List[JobPosting] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return jobs
            for j in r.json().get("jobs", []):
                loc = (j.get("location") or {}).get("name", "")
                jobs.append(JobPosting(
                    id=f"gh-{j.get('id', uuid.uuid4().hex[:8])}",
                    title=j.get("title", "Unknown"),
                    company=company_name,
                    location=loc or None,
                    url=j.get("absolute_url") or f"https://boards.greenhouse.io/{slug}/jobs/{j.get('id')}",
                    source=JobSource.greenhouse,
                    description=BeautifulSoup(j.get("content") or "", "lxml").get_text("\n")[:12000],
                    scraped_at=datetime.utcnow(),
                ))
    except Exception:
        pass
    return jobs


async def fetch_ashby(slug: str, company_name: str) -> List[JobPosting]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    jobs: List[JobPosting] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return jobs
            for j in r.json().get("jobs", []):
                jobs.append(JobPosting(
                    id=f"as-{j.get('id', uuid.uuid4().hex[:8])}",
                    title=j.get("title", "Unknown"),
                    company=company_name,
                    location=j.get("location") or None,
                    url=j.get("jobUrl") or j.get("applyUrl") or "",
                    source=JobSource.ashby,
                    description=(j.get("descriptionPlain") or j.get("descriptionHtml") or "")[:12000],
                    scraped_at=datetime.utcnow(),
                ))
    except Exception:
        pass
    return jobs


async def fetch_lever(slug: str, company_name: str) -> List[JobPosting]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    jobs: List[JobPosting] = []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return jobs
            for j in r.json():
                cats = j.get("categories") or {}
                desc_parts = [b.get("text", "") for b in (j.get("lists") or [])]
                jobs.append(JobPosting(
                    id=f"lv-{j.get('id', uuid.uuid4().hex[:8])}",
                    title=j.get("text", "Unknown"),
                    company=company_name,
                    location=cats.get("location") or None,
                    url=j.get("hostedUrl") or j.get("applyUrl") or "",
                    source=JobSource.lever,
                    description="\n".join(desc_parts)[:12000],
                    scraped_at=datetime.utcnow(),
                ))
    except Exception:
        pass
    return jobs


async def scan_company_boards(
    keywords: Optional[List[str]] = None,
    boards: Optional[List[dict]] = None,
) -> List[JobPosting]:
    keywords = [k.lower() for k in (keywords or [
        "ai advisor", "ai consultant", "ai strategy", "digital transformation",
        "ai ethics", "responsible ai", "ai transformation", "management consultant",
        "strategy consultant", "ai governance", "change management",
    ])]
    boards = boards or DEFAULT_BOARDS
    results: List[JobPosting] = []
    for b in boards:
        ats, slug, name = b["ats"], b["slug"], b["name"]
        if ats == "greenhouse":
            batch = await fetch_greenhouse(slug, name)
        elif ats == "ashby":
            batch = await fetch_ashby(slug, name)
        elif ats == "lever":
            batch = await fetch_lever(slug, name)
        else:
            batch = []
        for job in batch:
            blob = f"{job.title} {job.description}".lower()
            if any(k in blob for k in keywords):
                results.append(job)
    return results


def scrape_jobspy(
    search_term: str = "AI Consultant",
    location: str = "Remote",
    results_wanted: int = 25,
) -> List[JobPosting]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        return []
    try:
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=168,
        )
    except Exception:
        return []
    out: List[JobPosting] = []
    for _, row in df.iterrows():
        site = str(row.get("site", "other")).lower()
        source = JobSource.indeed if "indeed" in site else (
            JobSource.linkedin if "linkedin" in site else JobSource.other
        )
        out.append(JobPosting(
            id=str(uuid.uuid4())[:8],
            title=str(row.get("title") or "Unknown"),
            company=str(row.get("company") or "Unknown"),
            location=str(row.get("location") or "") or None,
            url=str(row.get("job_url") or row.get("url") or ""),
            source=source,
            description=str(row.get("description") or "")[:12000],
            scraped_at=datetime.utcnow(),
        ))
    return out


async def serper_job_links(query: str, num: int = 10) -> List[dict]:
    key = get_settings().serper_api_key
    if not key:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": num},
        )
        if r.status_code != 200:
            return []
        organic = r.json().get("organic") or []
        return [{"title": o.get("title"), "url": o.get("link"), "snippet": o.get("snippet")} for o in organic]
