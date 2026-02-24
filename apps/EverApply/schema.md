# EverApply Database Schema - Complete Reference

---

## Collection 1: EverApply_jobs

**Type:** Base collection

**Purpose:** Temporary storage for scraped jobs (24-48 hour lifespan)

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | auto | ✅ | Primary key |
| `title` | text | ✅ | Job title |
| `company` | text | ✅ | Company name |
| `description` | editor | ✅ | Full job description |
| `url` | url | ✅ | Link to original posting |
| `platform` | select | ✅ | `linkedin`, `indeed`, `ziprecruiter` |
| `salary_min` | number | ❌ | Minimum salary |
| `salary_max` | number | ❌ | Maximum salary |
| `posted_date` | date | ❌ | When job was posted |
| `scraped_at` | date | ✅ | When we found it |
| `is_active` | bool | ✅ | false = expired but kept for saved jobs |
| `created` | auto | ✅ | Auto timestamp |
| `updated` | auto | ✅ | Auto timestamp |

### Indexes

- `url` (unique) - Prevents duplicate jobs
- `company` - Fast company filtering
- `scraped_at` - For cleanup queries
- `is_active` - For finding active jobs

### API Rules

- **List/View:** `@request.auth.id != ""`
- **Create:** `@request.auth.id != ""`
- **Update:** `@request.auth.id != ""`
- **Delete:** `@request.auth.id != ""`

### Cleanup

Deleted nightly (except saved jobs marked `is_active = false`)

---

## Collection 2: EverApply_users

**Type:** Auth collection

**Purpose:** User accounts with resume and preferences

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | auto | ✅ | Primary key |
| `email` | auto | ✅ | Auth field |
| `password` | auto | ✅ | Auth field (hashed) |
| `tokenKey` | auto | ✅ | Auth field |
| `emailVisibility` | auto | ❌ | Auth field |
| `verified` | auto | ❌ | Auth field |
| `resume_text` | editor | ✅ | Full resume for AI matching |
| `target_keywords` | json | ✅ | Search terms (e.g., `["React", "Remote"]`) |
| `preferred_locations` | json | ✅ | Accepted locations (e.g., `["Remote", "Los Angeles", "Albuquerque"]`) |
| `scoring_model` | select | ✅ | `haiku`, `sonnet`, `hybrid` |
| `min_salary` | number | ❌ | Minimum acceptable salary |
| `min_match_score` | number | ✅ | Only show jobs >= this % (default: 70) |
| `max_applications_per_day` | number | ✅ | Rate limit for auto-apply (default: 10) |
| `anthropic_api_key` | text | ✅ | User's Claude API key (encrypted) |
| `api_key_valid` | bool | ✅ | Is key currently working? |
| `last_key_check` | date | ❌ | When we last verified key |
| `auto_apply_enabled` | bool | ✅ | Enable auto-apply feature |
| `auto_apply_threshold` | number | ✅ | Auto-apply if score >= this % (default: 85) |
| `created` | auto | ✅ | Auto timestamp |
| `updated` | auto | ✅ | Auto timestamp |

### Indexes

Default auth indexes (email, tokenKey)

### API Rules

Default auth rules

### Cleanup

Never deleted (permanent user accounts)

---

## Collection 3: EverApply_match_scores

**Type:** Base collection

**Purpose:** AI scoring results for user-job pairs (temporary, 24-hour lifespan)

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | auto | ✅ | Primary key |
| `user` | relation | ✅ | → EverApply_users |
| `job` | relation | ✅ | → EverApply_jobs |
| `score` | number | ✅ | Match percentage (0-100) |
| `reasons` | json | ❌ | Why it matched (e.g., `["Strong React match"]`) |
| `missing_skills` | json | ❌ | Skills user lacks (e.g., `["AWS", "Docker"]`) |
| `model_used` | select | ✅ | `haiku`, `sonnet`, `hybrid` |
| `confidence` | select | ❌ | `high`, `medium`, `low` |
| `scored_at` | date | ✅ | When scored |
| `created` | auto | ✅ | Auto timestamp |
| `updated` | auto | ✅ | Auto timestamp |

### Indexes

- `user, job` (unique) - One score per user-job pair
- `score` - For sorting by match %
- `user` - Fast user queries

### API Rules

- **List/View:** `@request.auth.id != "" && user = @request.auth.id`
- **Create:** `@request.auth.id != ""`
- **Update:** `@request.auth.id != "" && user = @request.auth.id`
- **Delete:** `@request.auth.id != "" && user = @request.auth.id`

### Cleanup

Deleted nightly (orphaned scores when jobs are deleted)

---

## Collection 4: EverApply_saved_jobs

**Type:** Base collection

**Purpose:** Jobs user bookmarked OR applied to (permanent storage)

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | auto | ✅ | Primary key |
| `user` | relation | ✅ | → EverApply_users |
| `job` | relation | ❌ | → EverApply_jobs (nullable after job deleted) |
| `company` | text | ✅ | Persists after job deleted |
| `title` | text | ✅ | Persists after job deleted |
| `url` | url | ✅ | Persists after job deleted |
| `save_type` | select | ✅ | `bookmarked`, `applied` |
| `status` | select | ❌ | `pending`, `applied`, `rejected`, `interview`, `offer` |
| `saved_at` | date | ✅ | When bookmarked/applied |
| `auto_applied` | bool | ❌ | true = bot applied it |
| `cover_letter` | editor | ❌ | Generated or custom cover letter |
| `notes` | editor | ❌ | Interview notes, feedback, etc. |
| `created` | auto | ✅ | Auto timestamp |
| `updated` | auto | ✅ | Auto timestamp |

### Indexes

- `user, job` (unique) - Can't save same job twice
- `user, save_type` - Filter bookmarks vs applications
- `saved_at` - Sort by when saved

### API Rules

- **List/View:** `@request.auth.id != "" && user = @request.auth.id`
- **Create:** `@request.auth.id != ""`
- **Update:** `@request.auth.id != "" && user = @request.auth.id`
- **Delete:** `@request.auth.id != "" && user = @request.auth.id`

### Cleanup

Never deleted (permanent saved jobs)

---

## Collection 5: EverApply_blacklisted_companies

**Type:** Base collection

**Purpose:** Companies user never wants to see

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | auto | ✅ | Primary key |
| `user` | relation | ✅ | → EverApply_users |
| `company_name` | text | ✅ | Original company name (e.g., "Indica Labs") |
| `normalized_name` | text | ✅ | For fuzzy matching (e.g., "indicalab") |
| `match_similar` | bool | ✅ | Enable fuzzy matching |
| `similarity_threshold` | number | ✅ | Fuzzy match % (0-100, default: 85) |
| `reason` | select | ❌ | `previously_worked`, `bad_culture`, `other` |
| `added_at` | date | ✅ | When blacklisted |
| `created` | auto | ✅ | Auto timestamp |
| `updated` | auto | ✅ | Auto timestamp |

### Indexes

- `user, normalized_name` - Fast fuzzy matching
- `user` - User's blacklist

### API Rules

- **List/View:** `@request.auth.id != "" && user = @request.auth.id`
- **Create:** `@request.auth.id != ""`
- **Update:** `@request.auth.id != "" && user = @request.auth.id`
- **Delete:** `@request.auth.id != "" && user = @request.auth.id`

### Cleanup

Never deleted (permanent blacklist)

---

## Database Summary

| Metric | Value |
|--------|-------|
| **Total Collections** | 5 |
| **Total Fields** | 61 (including auto fields) |
| **Total Indexes** | 11 |
| **Job Type** | Remote + user-specified locations |
| **Job Retention** | 24 hours (unless saved/applied) |
| **Score Retention** | 24 hours (cleaned with jobs) |
| **Saved Jobs Retention** | Permanent |
| **Blacklist Retention** | Permanent |

---

## Data Lifecycle

### Morning Cron (6:00 AM)

1. For each user, scrape jobs matching their `target_keywords` and `preferred_locations`
2. Save to `EverApply_jobs` (~200 records per user)
3. Score jobs against user's `resume_text` → `EverApply_match_scores`
4. Filter by `min_match_score`, blacklisted companies, and `min_salary`
5. User sees fresh matches

### User Actions (Throughout Day)

- Save job → `EverApply_saved_jobs` (save_type: bookmarked)
- Apply to job → `EverApply_saved_jobs` (save_type: applied)
- Blacklist company → `EverApply_blacklisted_companies`

### Night Cron (11:00 PM)

1. Delete unsaved jobs from `EverApply_jobs`
2. Delete orphaned scores from `EverApply_match_scores`
3. Mark saved jobs as `is_active = false` (keep data)

### Next Morning

- Fresh batch of jobs and scores
- Saved/applied jobs persist
- Blacklist persists

---
