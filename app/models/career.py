"""Master career data models – single source of truth for non-technical AI Advisor / Consultant roles."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class Contact(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None  # City, Country or "Remote"
    linkedin: Optional[str] = None
    website: Optional[str] = None
    portfolio: Optional[str] = None


class Experience(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    start_date: str  # YYYY-MM or YYYY
    end_date: Optional[str] = None  # YYYY-MM or "Present"
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list)  # quantified achievements
    skills_used: list[str] = Field(default_factory=list)
    industry: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    description: str
    role: Optional[str] = None
    outcomes: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    date: Optional[str] = None


class Education(BaseModel):
    id: str
    degree: str
    institution: str
    location: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    id: str
    name: str
    issuer: str
    date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class SkillCategory(BaseModel):
    category: str  # e.g. "AI Strategy", "Consulting", "Change Management"
    skills: list[str]


class Preference(BaseModel):
    target_titles: list[str] = Field(
        default_factory=lambda: [
            "AI Advisor",
            "AI Consultant",
            "AI Strategy Consultant",
            "AI Transformation Consultant",
            "Digital Transformation Advisor",
            "AI Ethics Advisor",
            "AI Implementation Consultant",
        ]
    )
    seniority: list[str] = Field(default_factory=lambda: ["Mid", "Senior", "Lead", "Principal"])
    locations: list[str] = Field(default_factory=lambda: ["Remote", "Hybrid"])
    industries: list[str] = Field(default_factory=list)
    min_salary: Optional[int] = None
    keywords_must: list[str] = Field(default_factory=list)
    keywords_avoid: list[str] = Field(default_factory=list)
    remote_only: bool = False


class MasterCareer(BaseModel):
    """Single source of truth. All tailored resumes are generated from this."""
    contact: Contact
    professional_summary: Optional[str] = None  # long-form, AI can refine
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    skills: list[SkillCategory] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    preferences: Preference = Field(default_factory=Preference)
    raw_notes: Optional[str] = None  # free-form dump for intake

    class Config:
        json_schema_extra = {
            "example": {
                "contact": {
                    "full_name": "Alex Rivera",
                    "email": "alex@example.com",
                    "location": "Remote / Europe",
                }
            }
        }
