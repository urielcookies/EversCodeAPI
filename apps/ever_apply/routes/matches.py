from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import get_db
from apps.ever_apply.models import JobMatch, MatchStatus
from apps.ever_apply.schemas import JobMatchRead, MatchStatusUpdate
from apps.ever_apply.services.clerk import get_current_clerk_user
from apps.ever_apply.models import User

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
