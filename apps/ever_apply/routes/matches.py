from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from apps.ever_apply.models import JobMatch, MatchStatus, User
from apps.ever_apply.schemas import JobMatchRead, MatchStatusUpdate
from apps.ever_apply.services.clerk import get_current_clerk_user
from apps.ever_apply.services.ats_resume import _r2_client

router = APIRouter()


# GET /matches?status=new
# Returns job matches for the logged-in user filtered by status, sorted by score desc
@router.get("", response_model=list[JobMatchRead])
async def list_matches(
    status: MatchStatus = MatchStatus.NEW,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    # Look up the DB user from the Clerk JWT
    user_result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Call /users/me first.")

    result = await db.execute(
        select(JobMatch)
        .where(JobMatch.user_id == user.id, JobMatch.status == status)
        .options(selectinload(JobMatch.job))
        .order_by(JobMatch.score.desc())
    )
    return result.scalars().all()


# PUT /matches/{match_id}/status
# Update the status of a job match (applied, saved, dismissed)
@router.put("/{match_id}/status", response_model=JobMatchRead)
async def update_match_status(
    match_id: str,
    body: MatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    # Look up the DB user from the Clerk JWT
    user_result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Fetch the match — ensure it belongs to this user
    result = await db.execute(
        select(JobMatch)
        .where(JobMatch.id == match_id, JobMatch.user_id == user.id)
        .options(selectinload(JobMatch.job))
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    match.status = body.status
    await db.commit()
    await db.refresh(match)
    return match


# POST /matches/{match_id}/generate-ats-resume
# Generate an ATS-optimized resume PDF for this job match and store it in R2
@router.post("/{match_id}/generate-ats-resume")
async def generate_ats_resume(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    user_result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.resume_url or not user.parsed_data:
        raise HTTPException(status_code=400, detail="Upload a resume before generating an ATS resume.")

    result = await db.execute(
        select(JobMatch)
        .where(JobMatch.id == match_id, JobMatch.user_id == user.id)
        .options(selectinload(JobMatch.job))
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    # Return cached result — don't count against the daily limit
    if match.ats_resume_url:
        return {"ats_resume_url": match.ats_resume_url}

    # Daily limit check
    daily_limit = settings.ATS_DAILY_LIMIT_FREE if user.is_free else settings.ATS_DAILY_LIMIT_PAID
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count_result = await db.execute(
        select(func.count()).where(
            JobMatch.user_id == user.id,
            JobMatch.ats_resume_generated_at >= today_start,
        )
    )
    if count_result.scalar() >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily ATS resume limit of {daily_limit} reached. Try again tomorrow.",
        )

    if not match.job.description:
        raise HTTPException(status_code=400, detail="Job has no description to generate from.")

    from apps.ever_apply.services.ats_resume import (
        download_resume_text,
        generate_ats_content,
        build_pdf,
        upload_ats_resume,
    )

    resume_text = await download_resume_text(user.resume_url)
    ats_data = await generate_ats_content(resume_text, match.job.description)
    pdf_bytes = build_pdf(ats_data)
    ats_url = await upload_ats_resume(pdf_bytes, clerk_user["sub"], match_id)

    match.ats_resume_url = ats_url
    match.ats_resume_generated_at = datetime.utcnow()
    user.total_ats_resumes_generated = (user.total_ats_resumes_generated or 0) + 1
    await db.commit()

    return {"ats_resume_url": ats_url}


# GET /matches/{match_id}/ats-resume
# Proxy the ATS resume PDF from R2 — avoids CORS issues with direct R2 URLs
@router.get("/{match_id}/ats-resume")
async def get_ats_resume(
    match_id: str,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    user_result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    result = await db.execute(
        select(JobMatch).where(JobMatch.id == match_id, JobMatch.user_id == user.id)
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")

    if not match.ats_resume_url:
        raise HTTPException(status_code=404, detail="ATS resume not generated yet.")

    key = urlparse(match.ats_resume_url).path.lstrip("/")
    response = _r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
    pdf_bytes = response["Body"].read()

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=ats-resume-{match_id}.pdf"},
    )
