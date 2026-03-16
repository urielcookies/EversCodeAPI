import enum
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class MatchStatus(str, enum.Enum):
    NEW = "new"
    SAVED = "saved"
    APPLIED = "applied"
    DISMISSED = "dismissed"

class RemoteType(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"

class Seniority(str, enum.Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"

class User(Base):
    __tablename__ = "everapply_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    resume_url = Column(String, nullable=True)
    parsed_data = Column(JSONB, nullable=True)
    preferences = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    matches = relationship("JobMatch", back_populates="user")

class Job(Base):
    __tablename__ = "everapply_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    remote_type = Column(Enum(RemoteType), nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=False)
    source_url = Column(String, unique=True, nullable=False)
    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    matches = relationship("JobMatch", back_populates="job")

class JobMatch(Base):
    __tablename__ = "everapply_jobmatches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("everapply_users.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("everapply_jobs.id"), nullable=False)
    score = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(Enum(MatchStatus), default=MatchStatus.NEW, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="matches")
    job = relationship("Job", back_populates="matches")
