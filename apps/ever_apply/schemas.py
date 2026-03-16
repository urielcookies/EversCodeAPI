from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from apps.ever_apply.models import MatchStatus, RemoteType, Seniority


class ParsedData(BaseModel):
    skills: list[str]
    titles: list[str]
    seniority: Seniority
    years_exp: int
    summary: str


class UserPreferenceRead(BaseModel):
    min_score: float
    remote_type: RemoteType
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class UserPreferencesUpdate(BaseModel):
    min_score: Optional[float] = None
    remote_type: Optional[RemoteType] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class UserRead(BaseModel):
    id: UUID
    clerk_user_id: str
    email: str
    resume_url: Optional[str] = None
    preferences: Optional[UserPreferenceRead] = None
    model_config = {"from_attributes": True}


class JobRead(BaseModel):
    id: UUID
    title: str
    company: str
    location: Optional[str] = None
    remote_type: Optional[RemoteType] = None
    source_url: str
    expires_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class JobMatchRead(BaseModel):
    id: UUID
    score: float
    reason: Optional[str] = None
    status: MatchStatus
    job: JobRead
    model_config = {"from_attributes": True}


class MatchStatusUpdate(BaseModel):
    status: MatchStatus
