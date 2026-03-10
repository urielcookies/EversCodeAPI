# EversCodeAPI

Production-ready FastAPI backend with async PostgreSQL, SQLAdmin, Server-Sent Events via PostgreSQL LISTEN/NOTIFY, Docker, and Railway deployment.

---

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL via SQLAlchemy (async + asyncpg) |
| Templates | Jinja2 |
| Admin UI | SQLAdmin at `/admin` |
| Realtime | PostgreSQL LISTEN/NOTIFY + SSE |
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
# Edit .env with your DATABASE_URL, SECRET_KEY, ENV
```

### Run the dev server

```bash
docker-compose up --build or uvicorn main:app --reload
```

Visit:
- API docs: http://localhost:8000/docs
- Admin: http://localhost:8000/admin
- App One SSE test: http://localhost:8000/app-one/
- App Two SSE test: http://localhost:8000/app-two/

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

The `web` service DATABASE_URL is automatically set to point at the `db` service inside Docker — no manual change needed.

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://user:pass@localhost:5432/mydb` |
| `SECRET_KEY` | Signs the SQLAdmin session cookie | `change-me-in-production` |
| `ADMIN_USERNAME` | Admin UI login username | `admin` |
| `ADMIN_PASSWORD` | Admin UI login password | `change-me-in-production` |
| `ENV` | `development` or `production` | `development` |

> For Docker Compose you can also set `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` to configure the `db` service.

---

## Railway Deployment

1. Push this repo to GitHub.
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo → select your repo.
3. Click **+ Add** → **Database** → **PostgreSQL** — Railway creates a separate cloud DB.
4. Click your **web service** → **Variables** → click **"Trying to connect a database? Add Variable"** → select **DATABASE_URL** from the dropdown. This links your app to the Railway Postgres service.
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

## Realtime (SSE)

Each app has its own PostgreSQL channel. The browser connects once and receives a stream of events.

### Browser

```js
const es = new EventSource('/app-one/sse');
es.onmessage = (e) => console.log(JSON.parse(e.data));
```

### Send a notification from psql

```sql
NOTIFY app_one_updates, '{"id": 1, "action": "created"}';
```

### Add a PostgreSQL trigger

```sql
CREATE OR REPLACE FUNCTION notify_app_one() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('app_one_updates', row_to_json(NEW)::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER app_one_insert_notify
  AFTER INSERT ON items
  FOR EACH ROW EXECUTE FUNCTION notify_app_one();
```

---

## Project Structure

```
.
├── core/
│   ├── config.py       # pydantic-settings BaseSettings
│   ├── database.py     # async SQLAlchemy engine + get_db dependency
│   └── realtime.py     # LISTEN/NOTIFY manager + SSE generator
├── apps/
│   ├── app_one/
│   │   ├── models.py   # Item model
│   │   ├── routes.py   # /app-one endpoints + SSE
│   │   └── admin.py    # SQLAdmin ItemAdmin view
│   └── app_two/
│       ├── models.py   # Note model
│       ├── routes.py   # /app-two endpoints + SSE
│       └── admin.py    # SQLAdmin NoteAdmin view
├── templates/
│   └── sse_test.html   # Browser SSE tester
├── main.py             # App factory, lifespan, router + admin mounts
├── Dockerfile
├── docker-compose.yml
├── railway.toml
└── requirements.txt
```
