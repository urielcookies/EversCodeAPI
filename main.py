from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from core.config import settings
from core.database import engine
from core.realtime import realtime


from apps.app_one.routes import router as app_one_router
from apps.app_two.routes import router as app_two_router
from apps.app_one.admin import ItemAdmin
from apps.app_two.admin import NoteAdmin, TagAdmin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # Tables are managed by Alembic
    # Start listening on each app's PostgreSQL channel
    # app_one does not use realtime — only app_two listens
    await realtime.listen("app_two_updates")

    yield

    # --- Shutdown ---
    await realtime.unlisten("app_two_updates")
    await engine.dispose()


app = FastAPI(
    title="EversCodeAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# Trust Railway's reverse proxy so HTTPS is correctly detected
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.TRUSTED_HOSTS)

# --- Routers ---
app.include_router(app_one_router, prefix="/app-one", tags=["app_one"])
app.include_router(app_two_router, prefix="/app-two", tags=["app_two"])

# --- Admin ---
# SECRET_KEY signs the admin session cookie
admin = Admin(app, engine, base_url="/admin", title="EversCodeAPI Admin")
# app_one
admin.add_view(ItemAdmin)

# app_two
admin.add_view(NoteAdmin)
admin.add_view(TagAdmin)

# --- Static files (create a /static dir if you need to serve assets) ---
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"status": "ok", "env": settings.ENV}
