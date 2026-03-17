from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from datetime import datetime

CLEARANCE_KEYWORDS = ["clearance", "ts/sci", "top secret", "dod clearance", "secret clearance", "security clearance"]

def requires_clearance(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in CLEARANCE_KEYWORDS)

from core.config import settings
from core.database import get_db
from apps.ever_apply.models import Job, JobMatch, User

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

    # Delete expired jobs not in the protected set
    result = await db.execute(
        delete(Job).where(
            Job.expires_at < datetime.utcnow(),
            Job.id.not_in(protected_ids),
        )
    )
    await db.commit()
    return {"deleted": result.rowcount}


# POST /admin/fetch
# Manually trigger a scrape + score run for all users
@router.post("/fetch", dependencies=[Depends(verify_admin_key)])
async def trigger_fetch(db: AsyncSession = Depends(get_db)):
    from apps.ever_apply.services.scraper import fetch_all_jobs
    from apps.ever_apply.services.scoring import score_match

    # Fetch all users who have a parsed resume
    users_result = await db.execute(
        select(User).where(User.parsed_data.isnot(None))
    )
    users = users_result.scalars().all()

    # Build keyword list from all users' parsed titles — deduplicated, capped at 5
    all_titles = []
    for u in users:
        all_titles += (u.parsed_data or {}).get("titles", [])
    keywords = list(dict.fromkeys(all_titles))[:5] or ["software engineer", "developer"]

    jobs = await fetch_all_jobs(keywords=keywords)

    matched = 0
    for job_data in jobs:
        # Skip jobs with no source_url
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
            await db.flush()  # Get job.id without committing

        # Score against each user's resume
        for user in users:
            summary = user.parsed_data.get("summary", "")
            skills = ", ".join(user.parsed_data.get("skills", []))
            resume_context = f"Summary: {summary}\nSkills: {skills}"
            description = job_data.get("description", "")
            if not summary or not description:
                continue

            if (user.preferences or {}).get("exclude_clearance") and requires_clearance(description):
                continue

            result = await score_match(resume_context, description)
            score = result.get("score", 0)
            reason = result.get("reason", "")

            # Only create match if above user's min score threshold
            min_score = (user.preferences or {}).get("min_score", 70)
            if score >= min_score:
                existing_match = await db.execute(
                    select(JobMatch).where(
                        and_(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
                    )
                )
                if existing_match.scalar_one_or_none() is None:
                    db.add(JobMatch(user_id=user.id, job_id=job.id, score=score, reason=reason))
                    matched += 1

    await db.commit()
    return {"jobs_fetched": len(jobs), "matches_created": matched}


# POST /admin/score
# Score existing DB jobs against all users — no Apify call
@router.post("/score", dependencies=[Depends(verify_admin_key)])
async def trigger_score(db: AsyncSession = Depends(get_db)):
    from apps.ever_apply.services.scoring import score_match

    users_result = await db.execute(
        select(User).where(User.parsed_data.isnot(None))
    )
    users = users_result.scalars().all()

    jobs_result = await db.execute(select(Job).where(Job.description != ""))
    jobs = jobs_result.scalars().all()

    matched = 0
    scored = 0
    for user in users:
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
