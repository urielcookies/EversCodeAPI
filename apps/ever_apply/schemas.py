import enum
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from apps.ever_apply.models import MatchStatus, RemoteType, Seniority


class RadiusMiles(int, enum.Enum):
    FIVE = 5
    TEN = 10
    FIFTEEN = 15
    TWENTY_FIVE = 25
    FIFTY = 50
    HUNDRED = 100


class ParsedData(BaseModel):
    name: Optional[str] = None
    skills: list[str]
    titles: list[str]
    seniority: Seniority
    years_exp: int
    summary: str


class UserPreferenceRead(BaseModel):
    min_score: float
    remote_type: Optional[RemoteType] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    preferred_location: Optional[str] = None
    radius_miles: Optional[RadiusMiles] = None
    exclude_clearance: bool = False


class ParsedDataUpdate(BaseModel):
    skills: Optional[list[str]] = None
    seniority: Optional[Seniority] = None
    years_exp: Optional[int] = None
    titles: Optional[list[str]] = None
    summary: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    min_score: Optional[float] = None
    remote_type: Optional[RemoteType] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    preferred_location: Optional[str] = None
    radius_miles: Optional[RadiusMiles] = None
    exclude_clearance: Optional[bool] = None


class UserRead(BaseModel):
    id: UUID
    clerk_user_id: str
    email: str
    resume_url: Optional[str] = None
    is_whitelisted: bool = False
    is_paid: bool = False
    trial_expired: bool = False
    trial_expires_at: Optional[datetime] = None
    parsed_data: Optional[ParsedData] = None
    preferences: Optional[UserPreferenceRead] = None
    model_config = {"from_attributes": True}


class JobRead(BaseModel):
    id: UUID
    title: str
    company: str
    location: Optional[str] = None
    remote_type: Optional[RemoteType] = None
    source_url: str
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class JobMatchRead(BaseModel):
    id: UUID
    score: float
    reason: Optional[str] = None
    status: MatchStatus
    ats_resume_url: Optional[str] = None
    job: JobRead
    model_config = {"from_attributes": True}


class MatchStatusUpdate(BaseModel):
    status: MatchStatus
