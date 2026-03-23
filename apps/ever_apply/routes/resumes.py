from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.database import get_db
from apps.ever_apply.models import User
from apps.ever_apply.services.clerk import get_current_clerk_user
from apps.ever_apply.services.ats_resume import download_resume_text, generate_ats_content, generate_ideal_content, build_pdf

router = APIRouter()

MT = ZoneInfo("America/Denver")
MAX_JOB_DESCRIPTION_CHARS = 15_000


class TargetedResumeRequest(BaseModel):
    job_description: str

    @field_validator("job_description")
    @classmethod
    def truncate(cls, v: str) -> str:
        return v[:MAX_JOB_DESCRIPTION_CHARS]


def _get_targeted_limit(user: User) -> int:
    if user.is_whitelisted:
        return settings.ATS_TARGETED_LIMIT_WHITELISTED
    if user.is_paid:
        return settings.ATS_TARGETED_LIMIT_PAID
    return settings.ATS_TARGETED_LIMIT_DEFAULT


def _reset_if_needed(user: User) -> None:
    """Reset custom_ats_count if last reset was before today MT."""
    today_mt = datetime.now(MT).date()
    last_reset = user.custom_ats_last_reset
    if last_reset is None:
        user.custom_ats_count = 0
        user.custom_ats_last_reset = datetime.utcnow()
        return
    # Convert stored naive UTC to MT for date comparison
    last_reset_mt = last_reset.replace(tzinfo=timezone.utc).astimezone(MT).date()
    if last_reset_mt < today_mt:
        user.custom_ats_count = 0
        user.custom_ats_last_reset = datetime.utcnow()


# POST /resumes/targeted
# Generate an ATS-optimized resume from a pasted job description — no match required
@router.post("/targeted")
async def generate_targeted_resume(
    body: TargetedResumeRequest,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.resume_url:
        raise HTTPException(status_code=400, detail="Upload a resume before generating a targeted resume.")

    if user.trial_expired:
        raise HTTPException(status_code=403, detail="Your trial has expired. Upgrade to continue.")

    # Reset daily counter if needed
    _reset_if_needed(user)

    daily_limit = _get_targeted_limit(user)
    if user.custom_ats_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily targeted resume limit of {daily_limit} reached. Resets at midnight MT.",
        )

    resume_text = await download_resume_text(user.resume_url)
    ats_data = await generate_ats_content(resume_text, body.job_description)
    pdf_bytes = build_pdf(ats_data)

    # Increment counter and lifetime total
    user.custom_ats_count += 1
    user.total_ats_resumes_generated = (user.total_ats_resumes_generated or 0) + 1
    await db.commit()

    name = ats_data.get("name", "Resume")
    filename = f"{name} - Resume.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


# POST /resumes/ideal
# Sandbox: generate a fictional ideal candidate resume for a given job description — no base resume required
@router.post("/ideal")
async def generate_ideal_resume(
    body: TargetedResumeRequest,
    clerk_user: dict = Depends(get_current_clerk_user),
):
    ats_data = await generate_ideal_content(body.job_description)
    pdf_bytes = build_pdf(ats_data)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=\"Ideal Candidate - Resume.pdf\""},
    )


# GET /resumes/targeted/usage
# Returns the user's daily targeted resume usage
@router.get("/targeted/usage")
async def get_targeted_usage(
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    _reset_if_needed(user)
    await db.commit()

    daily_limit = _get_targeted_limit(user)
    used = user.custom_ats_count
    return {
        "used": used,
        "limit": daily_limit,
        "remaining": max(0, daily_limit - used),
    }
