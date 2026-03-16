import httpx
from datetime import datetime, timedelta
from apify_client import ApifyClient
from core.config import settings

# Initialize Apify client
apify = ApifyClient(settings.APIFY_API_TOKEN)


def _normalize_job(raw: dict, source: str) -> dict:
    """Normalize a raw job dict from any source into the Job model shape."""
    posted_at = raw.get("posted_at") or raw.get("postedAt") or raw.get("date")
    if isinstance(posted_at, str):
        try:
            posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        except ValueError:
            posted_at = datetime.utcnow()
    elif not posted_at:
        posted_at = datetime.utcnow()

    location = raw.get("location") or raw.get("jobLocation", "")
    if isinstance(location, dict):
        location = location.get("formattedAddressShort") or location.get("formattedAddressLong") or ""

    return {
        "title": raw.get("title") or raw.get("jobTitle", ""),
        "company": raw.get("company") or raw.get("companyName", ""),
        "description": raw.get("description") or raw.get("jobDescription") or raw.get("descriptionText") or raw.get("descriptionHtml", ""),
        "location": location,
        "remote_type": raw.get("remote_type") or raw.get("workType", None),
        "salary_min": raw.get("salary_min") or raw.get("salaryMin", None),
        "salary_max": raw.get("salary_max") or raw.get("salaryMax", None),
        "posted_at": posted_at,
        "expires_at": posted_at + timedelta(hours=24),
        "source": source,
        "source_url": raw.get("url") or raw.get("jobUrl") or raw.get("applyUrl", ""),
        "raw_json": raw,
    }


async def fetch_indeed_jobs(keywords: list[str], location: str = "") -> list[dict]:
    """Scrape Indeed jobs via Apify actor borderline/indeed-scraper (PPR)."""
    run_input = {
        "country": "us",
        "query": " ".join(keywords),
        "location": location,
        "maxRows": 50,
        "fromDays": "1",
        "saveOnlyUniqueJobs": True,
    }
    run = apify.actor("borderline/indeed-scraper").call(run_input=run_input)
    items = apify.dataset(run["defaultDatasetId"]).iterate_items()
    return [_normalize_job(item, "indeed") for item in items]


async def fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs directly from Greenhouse public API — no Apify needed."""
    url = f"https://boards.greenhouse.io/{company_slug}/jobs.json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
    return [_normalize_job(job, "greenhouse") for job in jobs]


async def fetch_lever_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs directly from Lever public API — no Apify needed."""
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        jobs = response.json()
    return [_normalize_job(job, "lever") for job in jobs]


async def fetch_all_jobs(keywords: list[str], location: str = "") -> list[dict]:
    """Run all scrapers and return combined deduplicated job list."""
    all_jobs = []

    # Apify scraper (Indeed)
    all_jobs += await fetch_indeed_jobs(keywords, location)

    # Deduplicate by source_url before returning
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["source_url"] and job["source_url"] not in seen:
            seen.add(job["source_url"])
            unique_jobs.append(job)

    return unique_jobs
