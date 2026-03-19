from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from apps.ever_apply.models import Job
from apps.ever_apply.schemas import JobRead
from apps.ever_apply.services.clerk import get_current_clerk_user

router = APIRouter()


# GET /jobs
# Returns all jobs in the DB, sorted by posted_at desc
@router.get("", response_model=list[JobRead])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    result = await db.execute(
        select(Job).order_by(Job.posted_at.desc())
    )
    return result.scalars().all()
