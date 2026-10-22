"""Job posting and scoring models."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class JobSource(str, Enum):
    greenhouse = "greenhouse"
    ashby = "ashby"
    lever = "lever"
    workable = "workable"
    linkedin = "linkedin"
    indeed = "indeed"
    company = "company"
    manual = "manual"
    other = "other"


class PipelineStage(str, Enum):
    saved = "saved"
    scored = "scored"
    tailored = "tailored"
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    closed = "closed"


class JobPosting(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    remote: Optional[bool] = None
    url: str
    source: JobSource = JobSource.manual
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    salary_text: Optional[str] = None
    posted_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    raw_html: Optional[str] = None


class FitDimension(BaseModel):
    name: str  # skills, level, domain, location, legitimacy
    score: float  # 0-5
    evidence: str
    gaps: list[str] = Field(default_factory=list)


class JobScore(BaseModel):
    job_id: str
    overall: float  # 0-5
    dimensions: list[FitDimension] = Field(default_factory=list)
    recommendation: str  # "apply", "maybe", "skip"
    evidence_map: list[dict] = Field(default_factory=list)  # {jd_req, master_proof, strength}
    scored_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class TrackedJob(BaseModel):
    job: JobPosting
    score: Optional[JobScore] = None
    stage: PipelineStage = PipelineStage.saved
    tailored_resume_path: Optional[str] = None
    tailored_docx_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    applied_at: Optional[datetime] = None
    notes: list[str] = Field(default_factory=list)
    follow_up_date: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
