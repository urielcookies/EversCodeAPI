import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("ever_apply.scheduler")

scheduler = AsyncIOScheduler()

CLEARANCE_KEYWORDS = ["clearance", "ts/sci", "top secret", "dod clearance", "secret clearance", "security clearance"]


def _requires_clearance(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in CLEARANCE_KEYWORDS)


async def cleanup_job():
    """Delete expired jobs that haven't been saved or applied."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select, delete
    from datetime import datetime
    from apps.ever_apply.models import Job, JobMatch

    try:
        async with AsyncSessionLocal() as db:
            protected = await db.execute(
                select(JobMatch.job_id).where(
                    JobMatch.status.in_(["saved", "applied"])
                )
            )
            protected_ids = {row[0] for row in protected.fetchall()}

            result = await db.execute(
                delete(Job).where(
                    Job.expires_at < datetime.utcnow(),
                    Job.id.not_in(protected_ids),
                )
            )
            await db.commit()
            logger.info(f"cleanup_job: deleted {result.rowcount} expired jobs")
    except Exception:
        logger.exception("cleanup_job failed")


async def fetch_and_score():
    """Fetch new jobs from Indeed and score them against all users."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    from apps.ever_apply.models import Job, JobMatch, User
    from apps.ever_apply.services.scraper import fetch_all_jobs
    from apps.ever_apply.services.scoring import score_match

    logger.info("fetch_and_score: starting")
    try:
        async with AsyncSessionLocal() as db:
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
            logger.info(f"fetch_and_score: fetched {len(jobs)} jobs with keywords {keywords}, scoring against {len(users)} users")

            matched = 0
            for job_data in jobs:
                if not job_data.get("source_url"):
                    continue

                existing = await db.execute(
                    select(Job).where(Job.source_url == job_data["source_url"])
                )
                job = existing.scalar_one_or_none()
                if not job:
                    job = Job(**{k: v for k, v in job_data.items() if k != "raw_json"}, raw_json=job_data.get("raw_json"))
                    db.add(job)
                    await db.flush()

                for user in users:
                    summary = user.parsed_data.get("summary", "")
                    skills = ", ".join(user.parsed_data.get("skills", []))
                    resume_context = f"Summary: {summary}\nSkills: {skills}"
                    description = job_data.get("description", "")
                    if not summary or not description:
                        continue

                    # Remote type filter
                    remote_pref = (user.preferences or {}).get("remote_type")
                    if remote_pref and job.remote_type and job.remote_type != remote_pref:
                        continue

                    # Location filter for onsite/hybrid
                    preferred_location = (user.preferences or {}).get("preferred_location")
                    if remote_pref in ("onsite", "hybrid") and preferred_location and job.location:
                        city = preferred_location.split(",")[0].strip().lower()
                        if city not in job.location.lower():
                            continue

                    # Clearance filter
                    if (user.preferences or {}).get("exclude_clearance") and _requires_clearance(description):
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

                    min_score = (user.preferences or {}).get("min_score", 70)
                    if score >= min_score:
                        db.add(JobMatch(user_id=user.id, job_id=job.id, score=score, reason=reason))
                        matched += 1

            await db.commit()
            logger.info(f"fetch_and_score: done — {matched} new matches created")
    except Exception:
        logger.exception("fetch_and_score failed")


# Weekdays — cleanup before fetch, then fetch + score twice a day
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="mon-fri", hour=6, minute=55))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=7, minute=0))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=10, minute=0))

# Weekends — cleanup + single fetch (conserve Apify credits)
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="sat,sun", hour=6, minute=55))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="sat,sun", hour=7, minute=0))
