# EverApply

Job application automation platform. Scrapes jobs from Indeed via Apify, scores them against a user's resume using DeepSeek, and surfaces ranked matches through a REST API.

---

## Architecture

```
apps/ever_apply/
├── models.py          # SQLAlchemy ORM — User, Job, JobMatch
├── schemas.py         # Pydantic request/response + enums (RadiusMiles, etc.)
├── admin.py           # SQLAdmin views (registered in main.py)
├── scheduler.py       # APScheduler cron jobs (fetch + score + cleanup)
├── services/
│   ├── clerk.py       # Clerk JWT verification (RS256 via JWKS)
│   ├── resume.py      # PDF extraction (pdfplumber) + DeepSeek parsing + R2 upload
│   ├── scraper.py     # Apify Indeed scraper + Greenhouse/Lever direct fetch
│   └── scoring.py     # DeepSeek resume-to-job scoring (0–100)
└── routes/
    ├── ping.py        # GET /ping — health check
    ├── users.py       # User upsert, resume upload, preferences
    ├── matches.py     # List + update match status
    └── admin.py       # Backend ops — fetch, score, cleanup (X-Admin-Key protected)
```

**Prefix:** `/ever-apply` (registered in `main.py`)
**DB tables:** `everapply_users`, `everapply_jobs`, `everapply_job_matches`

---

## API Routes

### User
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/users/me` | Upsert user from Clerk JWT (first login creates record) |
| `POST` | `/users/resume` | Upload PDF → extract text → DeepSeek parse → store in R2 |
| `GET`  | `/users/preferences` | Return preferences JSONB |
| `PUT`  | `/users/preferences` | Update preferences (partial update) |

### Matches
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/matches?status=new` | List matches for current user, ordered by score desc |
| `PUT`  | `/matches/{id}/status` | Update match status (`new`, `saved`, `applied`, `dismissed`) |

### Admin (`X-Admin-Key` required)
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/fetch` | Scrape Indeed via Apify → score all users → create matches |
| `POST` | `/admin/score` | Score existing DB jobs against all users (no Apify call) |
| `POST` | `/admin/cleanup` | Delete expired jobs not saved/applied |

---

## Pipeline

```
POST /admin/fetch
  └─ scraper.py        fetch_all_jobs()  →  50 jobs from Indeed
  └─ admin.py          upsert jobs into everapply_jobs
  └─ scoring.py        score_match(resume_context, job.description)  →  {score, reason}
  └─ admin.py          create JobMatch if score >= user.min_score

POST /admin/score      (same scoring step, skips the Apify call)

GET /matches?status=new
  └─ returns JobMatch rows joined to Job, filtered by user + status, sorted by score desc
```

---

## Scheduler

Runs inside the FastAPI process via APScheduler (no Redis/Celery needed).

| Schedule | Job |
|----------|-----|
| Mon–Fri 6:55am | cleanup |
| Mon–Fri 7:00am | fetch + score |
| Mon–Fri 7:15am | score only |
| Mon–Fri 10:00am | fetch + score |
| Mon–Fri 10:15am | score only |
| Sat–Sun 6:55am | cleanup |
| Sat–Sun 7:00am | fetch + score |

---

## Scoring

DeepSeek (`deepseek-chat`) acts as the scoring engine. No vector math or embeddings.

**Input:** `Summary: <one sentence>\nSkills: <comma-separated list>`
**Output:** `{"score": 85, "reason": "Strong React and TypeScript overlap, missing Go experience"}`

**Score guide:**
- `90–100` — strong match on all required skills + correct seniority
- `70–89` — matches core requirements, minor gaps in preferred skills
- `50–69` — partial match, missing one or more key required skills
- `< 50` — significant mismatch

---

## Services

### `clerk.py`
Verifies Clerk JWT using RS256 + JWKS. Called via `Depends(get_current_clerk_user)` on all user-facing routes. Returns the decoded payload (`sub` = `clerk_user_id`).

### `resume.py`
1. Upload PDF bytes to Cloudflare R2 (S3-compatible via boto3)
2. Extract text with pdfplumber (no temp files — uses `BytesIO`)
3. Send text to DeepSeek → structured `ParsedData` (skills, titles, seniority, years_exp, summary)
4. Store `parsed_data` JSONB + `resume_url` on the User record

### `scraper.py`
- **Indeed** — `borderline/indeed-scraper` Apify actor ($5/1000 jobs PPR). Returns up to 50 jobs posted in the last 24 hours.
- **Greenhouse/Lever** — direct public API calls (no Apify, no cost). Currently unused in `fetch_all_jobs` — add company slugs to enable.
- All sources normalized through `_normalize_job()` into the `Job` model shape.

### `scoring.py`
Single function `score_match(resume_context, job_description)`. Fires one DeepSeek chat completion with `response_format: json_object`. Returns `{score, reason}`.

---

## User Preferences

Stored as JSONB on `everapply_users.preferences`.

| Field | Type | Description |
|-------|------|-------------|
| `min_score` | `float` | Minimum match score to surface (e.g. 70) |
| `remote_type` | `RemoteType` | `remote`, `hybrid`, `onsite` |
| `preferred_location` | `str` | City/state for onsite/hybrid filtering (e.g. "Austin, TX") |
| `radius_miles` | `RadiusMiles` | `5, 10, 15, 25, 50, 100` |
| `salary_min` | `int` | Optional salary floor |
| `salary_max` | `int` | Optional salary ceiling |

---

## Environment Variables

```
CLERK_JWKS_URL           # Clerk Dashboard → API Keys
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL        # https://api.deepseek.com
APIFY_API_TOKEN
R2_ACCOUNT_ID            # Cloudflare Account ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME           # e.g. ever-apply-resumes
R2_PUBLIC_URL            # e.g. https://pub-xxx.r2.dev
EVER_APPLY_ADMIN_KEY     # Static key for /admin/* routes
```

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| UUID PKs | Prevents enumeration attacks on user/job IDs |
| `everapply_` table prefix | Avoids collision with other apps' `users`/`jobs` tables |
| JSONB for preferences | Schema-flexible; no migration needed to add new preference fields |
| DeepSeek over embeddings | Handles synonym reasoning natively — no pgvector, no numpy |
| APScheduler over Celery | No Redis dependency for Phase 1; swap if scale demands it |
| Cloudflare R2 | S3-compatible (boto3 works unchanged), zero egress fees |
| Admin routes as HTTP endpoints | Scheduler + manual curl + future automation all share the same code path |
