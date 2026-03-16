from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


scheduler = AsyncIOScheduler()


async def cleanup_job():
    """Delete expired jobs that haven't been saved or applied."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select, delete
    from datetime import datetime
    from apps.ever_apply.models import Job, JobMatch

    async with AsyncSessionLocal() as db:
        protected = await db.execute(
            select(JobMatch.job_id).where(
                JobMatch.status.in_(["saved", "applied"])
            )
        )
        protected_ids = {row[0] for row in protected.fetchall()}

        await db.execute(
            delete(Job).where(
                Job.expires_at < datetime.utcnow(),
                Job.id.not_in(protected_ids),
            )
        )
        await db.commit()


async def fetch_and_score():
    """Fetch new jobs and score them against all users."""
    from core.database import AsyncSessionLocal
    from sqlalchemy import select
    from apps.ever_apply.models import Job, JobMatch, User
    from apps.ever_apply.services.scraper import fetch_all_jobs
    from apps.ever_apply.services.scoring import score_match

    async with AsyncSessionLocal() as db:
        users_result = await db.execute(
            select(User).where(User.parsed_data.isnot(None))
        )
        users = users_result.scalars().all()

        jobs = await fetch_all_jobs(keywords=["software engineer", "developer"])

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
                description = job_data.get("description", "")
                if not summary or not description:
                    continue

                result = await score_match(summary, description)
                score = result.get("score", 0)
                reason = result.get("reason", "")

                min_score = (user.preferences or {}).get("min_score", 70)
                if score >= min_score:
                    match = JobMatch(
                        user_id=user.id,
                        job_id=job.id,
                        score=score,
                        reason=reason,
                    )
                    db.add(match)

        await db.commit()


# Weekdays — 2 fetch runs per day
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="mon-fri", hour=6, minute=55))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=7, minute=0))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="mon-fri", hour=10, minute=0))

# Weekends — cleanup + single fetch only (conserve Apify credits)
scheduler.add_job(cleanup_job, CronTrigger(day_of_week="sat,sun", hour=6, minute=55))
scheduler.add_job(fetch_and_score, CronTrigger(day_of_week="sat,sun", hour=7, minute=0))
