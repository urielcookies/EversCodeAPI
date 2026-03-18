from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime, timedelta

CLEARANCE_KEYWORDS = ["clearance", "ts/sci", "top secret", "dod clearance", "secret clearance", "security clearance"]

def requires_clearance(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in CLEARANCE_KEYWORDS)

from core.config import settings
from core.database import get_db
from apps.ever_apply.models import Job, JobMatch, User


def _is_eligible(user) -> bool:
    """Returns True if this user should receive an Apify fetch run."""
    if user.is_free:
        return True
    trial_cutoff = datetime.utcnow() - timedelta(days=settings.EVER_APPLY_TRIAL_DAYS)
    return user.created_at >= trial_cutoff


router = APIRouter()

# Admin routes are protected by a static API key, not Clerk JWT
api_key_header = APIKeyHeader(name="X-Admin-Key")


def verify_admin_key(key: str = Depends(api_key_header)):
    if key != settings.EVER_APPLY_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


# POST /admin/cleanup-jobs
# Deletes expired jobs that have not been saved or applied
@router.post("/cleanup-jobs", dependencies=[Depends(verify_admin_key)])
async def cleanup_jobs(db: AsyncSession = Depends(get_db)):
    # Find job IDs that are saved or applied — never delete these
    protected = await db.execute(
        select(JobMatch.job_id).where(
            JobMatch.status.in_(["saved", "applied"])
        )
    )
    protected_ids = {row[0] for row in protected.fetchall()}

    # Find expired job IDs that are safe to delete
    expired = await db.execute(
        select(Job.id).where(
            Job.expires_at < datetime.utcnow(),
            Job.id.not_in(protected_ids),
        )
    )
    expired_ids = [row[0] for row in expired.fetchall()]

    if not expired_ids:
        return {"deleted": 0}

    # Delete their matches first to satisfy the FK constraint
    await db.execute(delete(JobMatch).where(JobMatch.job_id.in_(expired_ids)))

    # Now delete the jobs
    result = await db.execute(delete(Job).where(Job.id.in_(expired_ids)))
    await db.commit()
    return {"deleted": result.rowcount}


# POST /admin/fetch
# Manually trigger a scrape + score run for all eligible users (per-user Apify call)
@router.post("/fetch", dependencies=[Depends(verify_admin_key)])
async def trigger_fetch(db: AsyncSession = Depends(get_db)):
    from apps.ever_apply.services.scraper import fetch_indeed_jobs
    from apps.ever_apply.services.scoring import score_match

    # Fetch all users who have a parsed resume
    users_result = await db.execute(
        select(User).where(User.parsed_data.isnot(None))
    )
    users = users_result.scalars().all()
    if not users:
        return {"jobs_fetched": 0, "matches_created": 0, "reason": "no users with resumes"}

    total_jobs = 0
    matched = 0
    for user in users:
        if not _is_eligible(user):
            continue

        # User-specific keywords from their parsed titles
        keywords = list(dict.fromkeys(user.parsed_data.get("titles", [])))[:5] or ["software engineer", "developer"]

        # Location: only pass it for onsite/hybrid users
        prefs = user.preferences or {}
        remote_pref = prefs.get("remote_type")
        location = prefs.get("preferred_location", "") if remote_pref in ("onsite", "hybrid") else ""

        jobs = await fetch_indeed_jobs(keywords, location)
        total_jobs += len(jobs)

        for job_data in jobs:
            if not job_data.get("source_url"):
                continue

            # Upsert job — skip if source_url already exists
            existing = await db.execute(
                select(Job).where(Job.source_url == job_data["source_url"])
            )
            job = existing.scalar_one_or_none()
            if not job:
                job = Job(**{k: v for k, v in job_data.items() if k != "raw_json"}, raw_json=job_data.get("raw_json"))
                db.add(job)
                await db.flush()

            summary = user.parsed_data.get("summary", "")
            skills = ", ".join(user.parsed_data.get("skills", []))
            resume_context = f"Summary: {summary}\nSkills: {skills}"
            description = job_data.get("description", "")
            if not summary or not description:
                continue

            if prefs.get("exclude_clearance") and requires_clearance(description):
                continue

            # Skip if already matched
            existing_match = await db.execute(
                select(JobMatch).where(
                    and_(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
                )
            )
            if existing_match.scalar_one_or_none() is not None:
                continue

            result = await score_match(resume_context, description)
            score = result.get("score", 0)
            reason = result.get("reason", "")
            min_score = prefs.get("min_score", 70)
            if score >= min_score:
                db.add(JobMatch(user_id=user.id, job_id=job.id, score=score, reason=reason))
                matched += 1

    await db.commit()
    return {"jobs_fetched": total_jobs, "matches_created": matched}


# POST /admin/score
# Score existing DB jobs against all users — no Apify call
@router.post("/score", dependencies=[Depends(verify_admin_key)])
async def trigger_score(db: AsyncSession = Depends(get_db)):
    from apps.ever_apply.services.scoring import score_match

    users_result = await db.execute(
        select(User).where(User.parsed_data.isnot(None))
    )
    users = users_result.scalars().all()
    if not users:
        return {"jobs_scored": 0, "matches_created": 0, "reason": "no users with resumes"}

    jobs_result = await db.execute(select(Job).where(Job.description != ""))
    jobs = jobs_result.scalars().all()

    matched = 0
    scored = 0
    for user in users:
        if not _is_eligible(user):
            continue

        # Only fetch jobs not already matched for this user — avoids redundant DeepSeek calls
        already_matched = await db.execute(
            select(JobMatch.job_id).where(JobMatch.user_id == user.id)
        )
        matched_job_ids = {row[0] for row in already_matched.fetchall()}

        unscored_jobs = [j for j in jobs if j.id not in matched_job_ids]

        for job in unscored_jobs:
            # Skip jobs that don't match user's remote preference
            remote_pref = (user.preferences or {}).get("remote_type")
            if remote_pref and job.remote_type and job.remote_type != remote_pref:
                continue

            # For onsite/hybrid, filter by preferred_location (city/state string match)
            preferred_location = (user.preferences or {}).get("preferred_location")
            if remote_pref in ("onsite", "hybrid") and preferred_location and job.location:
                city = preferred_location.split(",")[0].strip().lower()
                if city not in job.location.lower():
                    continue

            summary = user.parsed_data.get("summary", "")
            skills = ", ".join(user.parsed_data.get("skills", []))
            resume_context = f"Summary: {summary}\nSkills: {skills}"
            if not summary or not job.description:
                continue

            if (user.preferences or {}).get("exclude_clearance") and requires_clearance(job.description):
                continue

            result = await score_match(resume_context, job.description)
            score = result.get("score", 0)
            reason = result.get("reason", "")
            scored += 1

            min_score = (user.preferences or {}).get("min_score", 70)
            if score >= min_score:
                db.add(JobMatch(user_id=user.id, job_id=job.id, score=score, reason=reason))
                matched += 1

    await db.commit()
    return {"jobs_scored": scored, "matches_created": matched}
