import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import settings

logger = logging.getLogger("ever_apply.scheduler")

scheduler = AsyncIOScheduler()

CLEARANCE_KEYWORDS = ["clearance", "ts/sci", "top secret", "dod clearance", "secret clearance", "security clearance"]


def _requires_clearance(description: str) -> bool:
    desc = description.lower()
    return any(kw in desc for kw in CLEARANCE_KEYWORDS)


def _is_eligible(user) -> bool:
    """Returns True if this user should receive an Apify fetch run."""
    if user.is_whitelisted:
        return True
    trial_cutoff = datetime.utcnow() - timedelta(days=settings.EVER_APPLY_TRIAL_DAYS)
    return user.created_at >= trial_cutoff


async def cleanup_job():
    """Delete expired jobs that haven't been saved or applied, and clean up any ATS resume files from R2."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select, delete
    from datetime import datetime
    from apps.ever_apply.models import Job, JobMatch
    from apps.ever_apply.services.ats_resume import delete_ats_resume

    try:
        async with AsyncSessionLocal() as db:
            protected = await db.execute(
                select(JobMatch.job_id).where(
                    JobMatch.status.in_(["saved", "applied"])
                )
            )
            protected_ids = {row[0] for row in protected.fetchall()}

            expired = await db.execute(
                select(Job.id).where(
                    Job.expires_at < datetime.utcnow(),
                    Job.id.not_in(protected_ids),
                )
            )
            expired_ids = [row[0] for row in expired.fetchall()]

            if expired_ids:
                # Collect ATS resume URLs to delete from R2 after DB cleanup
                ats_result = await db.execute(
                    select(JobMatch.ats_resume_url).where(
                        JobMatch.job_id.in_(expired_ids),
                        JobMatch.ats_resume_url.isnot(None),
                    )
                )
                ats_urls = [row[0] for row in ats_result.fetchall()]

                await db.execute(delete(JobMatch).where(JobMatch.job_id.in_(expired_ids)))
                result = await db.execute(delete(Job).where(Job.id.in_(expired_ids)))
                await db.commit()

                for url in ats_urls:
                    try:
                        await delete_ats_resume(url)
                    except Exception:
                        logger.warning(f"cleanup_job: failed to delete ATS resume from R2: {url}")

                logger.info(f"cleanup_job: deleted {result.rowcount} expired jobs, {len(ats_urls)} ATS resumes")
            else:
                logger.info("cleanup_job: nothing to delete")
    except Exception:
        logger.exception("cleanup_job failed")


async def fetch_and_score():
    """Fetch new jobs from Indeed and score them — one Apify call per eligible user."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select, and_
    from apps.ever_apply.models import Job, JobMatch, User
    from apps.ever_apply.services.scraper import fetch_indeed_jobs
    from apps.ever_apply.services.scoring import score_match

    logger.info("fetch_and_score: starting")
    try:
        async with AsyncSessionLocal() as db:
            users_result = await db.execute(
                select(User).where(User.parsed_data.isnot(None))
            )
            users = users_result.scalars().all()
            if not users:
                logger.info("fetch_and_score: no users with resumes, skipping Apify call")
                return

            total_jobs = 0
            matched = 0
            for user in users:
                if not _is_eligible(user):
                    logger.info(f"fetch_and_score: skipping user {user.id} — trial expired")
                    continue

                # User-specific keywords from their parsed titles
                keywords = list(dict.fromkeys(user.parsed_data.get("titles", [])))[:5] or ["software engineer", "developer"]

                # Location: only pass it for onsite/hybrid users
                prefs = user.preferences or {}
                remote_pref = prefs.get("remote_type")
                location = prefs.get("preferred_location", "") if remote_pref in ("onsite", "hybrid") else ""

                logger.info(f"fetch_and_score: fetching for user {user.id} — keywords={keywords}, location={location!r}")
                jobs = await fetch_indeed_jobs(keywords, location, remote=remote_pref == "remote")
                total_jobs += len(jobs)

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

                    summary = user.parsed_data.get("summary", "")
                    skills = ", ".join(user.parsed_data.get("skills", []))
                    resume_context = f"Summary: {summary}\nSkills: {skills}"
                    description = job_data.get("description", "")
                    if not summary or not description:
                        continue

                    # Remote type filter
                    if remote_pref and job.remote_type and job.remote_type != remote_pref:
                        continue

                    # Clearance filter
                    if prefs.get("exclude_clearance") and _requires_clearance(description):
                        continue

                    # Skip if already matched
                    existing_match = await db.execute(
                        select(JobMatch).where(
                            and_(JobMatch.user_id == user.id, JobMatch.job_id == job.id)
                        )
                    )
                    if existing_match.scalar_one_or_none() is not None:
                        continue

                    result = await score_match(resume_context, description, user_preferences=prefs)
                    score = result.get("score", 0)
                    reason = result.get("reason", "")

                    min_score = prefs.get("min_score", 70)
                    if score >= min_score:
                        db.add(JobMatch(user_id=user.id, job_id=job.id, score=score, reason=reason))
                        matched += 1

            await db.commit()
            logger.info(f"fetch_and_score: done — {total_jobs} jobs fetched, {matched} new matches created")
    except Exception:
        logger.exception("fetch_and_score failed")


MT = "America/Denver"

# Weekdays — cleanup before fetch, then fetch + score twice a day
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="mon-fri", hour=8, minute=55, timezone=MT))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone=MT))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=12, minute=0, timezone=MT))

# Weekends — cleanup + single fetch (conserve Apify credits)
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="sat,sun", hour=8, minute=55, timezone=MT))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="sat,sun", hour=9, minute=0, timezone=MT))
