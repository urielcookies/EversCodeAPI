# EversCodeAPI

Production-ready FastAPI backend with async PostgreSQL, SQLAdmin, Server-Sent Events via PostgreSQL LISTEN/NOTIFY, Docker, and Railway deployment.

---

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL via SQLAlchemy (async + asyncpg) |
| Admin UI | SQLAdmin at `/admin` |
| Realtime | PostgreSQL LISTEN/NOTIFY + SSE |
| Migrations | Alembic |
| Containers | Docker + Docker Compose |
| Deployment | Railway |

---

## Local Setup (Virtual Environment)

```bash
# 1. Create the virtual environment
python -m venv .venv

# 2. Activate it
# Mac / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ENV
```

### Run the dev server

```bash
# Option A: Docker (starts FastAPI + PostgreSQL together)
docker-compose up --build

# Option B: Local uvicorn (requires a running PostgreSQL instance)
uvicorn main:app --reload
```

Visit:
- API docs: http://localhost:8000/docs
- Admin UI: http://localhost:8000/admin
- Blog Demo SSE stream: http://localhost:8000/blog-demo/live

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://user:pass@localhost:5432/mydb` |
| `SECRET_KEY` | Signs the SQLAdmin session cookie | `change-me-in-production` |
| `ADMIN_USERNAME` | Admin UI login username | `admin` |
| `ADMIN_PASSWORD` | Admin UI login password | `change-me-in-production` |
| `ENV` | `development` or `production` | `development` |
| `BLOG_DEMO_API_KEY` | API key for all `/blog-demo/*` routes | `change-me-in-production` |

> For Docker Compose you can also set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` to configure the `db` service.

---

## Authentication

### API Key (blog_demo)

All `/blog-demo/*` routes require an `X-API-Key` header. Set `BLOG_DEMO_API_KEY` in your `.env` and pass the key on every request.

```bash
curl http://localhost:8000/blog-demo/posts \
  -H "X-API-Key: your-api-key-here"
```

```js
fetch('/blog-demo/posts', {
  headers: { 'X-API-Key': 'your-api-key-here' }
})
```

Missing or incorrect key returns `403 Forbidden`.

### Adding auth to a new app

1. Add a key to `Settings` in `core/config.py` (e.g. `YOUR_APP_API_KEY: str`)
2. Add the variable to `.env` and `.env.example`
3. Add a dependency in `core/security.py`
4. Pass it to `include_router` in `main.py`:
```python
app.include_router(your_router, dependencies=[Depends(your_auth_dependency)])
```

---

## Database Migrations (Alembic)

Migrations are handled by Alembic. The `Dockerfile` runs `alembic upgrade head` automatically on every deploy.

### Apply migrations locally

> PostgreSQL must be running before any Alembic command. Start it with `docker-compose up -d` if it isn't already.

```bash
alembic upgrade head
```

### After changing a model

Any time you add, remove, or modify a column or table, generate a new migration:

```bash
# PostgreSQL must be running
docker-compose up -d

alembic revision --autogenerate -m "describe_your_change"
alembic upgrade head
```

Alembic diffs your SQLAlchemy models against the current DB state and writes the migration file automatically. Review it in `alembic/versions/` before applying.

### Roll back the last migration

```bash
alembic downgrade -1
```

---

## Adding a New App

1. Create the app folder and files:

```
apps/
  your_app/
    __init__.py
    models.py    # SQLAlchemy models
    schemas.py   # Pydantic request/response models
    admin.py     # SQLAdmin views
    routes/
      __init__.py   # composes sub-routers
      health.py
      your_resource.py
```

2. Register the model with Alembic — add one line to `alembic/env.py`:

```python
import apps.your_app.models  # noqa: F401
```

3. Register the router and admin views in `main.py`:

```python
from apps.your_app.routes import router as your_app_router
from apps.your_app.admin import YourModelAdmin

app.include_router(your_app_router, prefix="/your-app", tags=["your_app"])
admin.add_view(YourModelAdmin)
```

4. Generate and apply the migration:

```bash
alembic revision --autogenerate -m "add_your_app_tables"
alembic upgrade head
```

---

## Realtime (SSE)

Each app has its own PostgreSQL channel. The browser connects once and receives a stream of events.

### How it works

1. On startup, `main.py` calls `realtime.listen("channel_name")` which opens a raw asyncpg connection
2. A route exposes a `StreamingResponse` using `realtime.sse_generator("channel_name")`
3. When your API fires `pg_notify`, all connected clients receive the event instantly

### Connect from the browser

```js
const es = new EventSource('/blog-demo/live');
es.addEventListener('connected', () => console.log('connected'));
es.onmessage = (e) => console.log(JSON.parse(e.data));
```

### Fire a notification from your API route

```python
import json
from sqlalchemy import text

payload = json.dumps({"event": "post_published", "title": "Hello World"})
await db.execute(text("SELECT pg_notify(:channel, :payload)"), {"channel": "blog_updates", "payload": payload})
await db.commit()
```

### Fire a notification from psql (ad-hoc testing)

```sql
NOTIFY blog_updates, '{"event": "post_published", "title": "Hello World"}';
```

### Register a new channel

In `main.py` lifespan:

```python
await realtime.listen("your_channel")   # startup
await realtime.unlisten("your_channel") # shutdown
```

---

## Docker

```bash
# Build and start both services (FastAPI + PostgreSQL)
docker-compose up --build

# Run in background
docker-compose up --build -d

# Tear down (keeps postgres_data volume)
docker-compose down
```

The `web` service `DATABASE_URL` is automatically set to point at the `db` service inside Docker — no manual change needed.

---

## Railway Deployment

1. Push this repo to GitHub.
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo → select your repo.
3. Click **+ Add** → **Database** → **PostgreSQL** — Railway creates a separate cloud DB.
4. Click your **web service** → **Variables** → click **"Trying to connect a database? Add Variable"** → select **DATABASE_URL** from the dropdown.
5. Add these variables manually:
   - `SECRET_KEY` → your generated secret key
   - `ADMIN_USERNAME` → your admin login username
   - `ADMIN_PASSWORD` → a strong password for the admin UI
   - `ENV` → `production`
   - Do NOT add `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, or `DATABASE_URL` as plain values — Railway manages those.
6. Click **Deploy** — Railway builds from the `Dockerfile`, runs `alembic upgrade head`, then starts the server.

Every `git push origin main` after this triggers an automatic redeploy.

### Viewing prod data (TablePlus / pgAdmin)

1. Open your Railway **Postgres** service → **Variables**
2. Copy `DATABASE_PUBLIC_URL`
3. In TablePlus: New Connection → PostgreSQL → paste the URL → Test → Connect

---

## Project Structure

```
.
├── core/
│   ├── config.py        # pydantic-settings BaseSettings (reads .env)
│   ├── database.py      # async SQLAlchemy engine + get_db dependency
│   ├── realtime.py      # LISTEN/NOTIFY manager + SSE generator
│   └── auth.py          # SQLAdmin authentication backend
├── apps/
│   ├── app_one/
│   │   ├── models.py    # Item model
│   │   ├── routes.py    # /app-one endpoints
│   │   └── admin.py     # SQLAdmin ItemAdmin view
│   └── blog_demo/
│       ├── models.py    # Post, Category models
│       ├── schemas.py   # Pydantic PostCreate, PostRead, CategoryRead, etc.
│       ├── admin.py     # SQLAdmin PostAdmin, CategoryAdmin views
│       └── routes/
│           ├── __init__.py       # composes all sub-routers
│           ├── health.py         # GET /blog-demo/test
│           ├── posts.py          # CRUD /blog-demo/posts
│           ├── categories.py     # GET /blog-demo/categories
│           └── sse.py            # GET /blog-demo/live (SSE stream)
├── alembic/
│   ├── env.py           # Alembic runner — add model imports here for new apps
│   └── versions/        # Auto-generated migration files
├── templates/
│   └── sse_test.html    # Browser SSE tester
├── main.py              # App factory, lifespan, router + admin mounts
├── Dockerfile
├── docker-compose.yml
├── railway.toml
└── requirements.txt
```
