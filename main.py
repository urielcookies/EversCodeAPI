from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin

from core.auth import authentication_backend
from core.config import settings
from core.database import engine
from core.realtime import realtime


from apps.app_one.routes import router as app_one_router
from apps.blog_demo.routes import router as blog_demo_router
from apps.app_one.admin import ItemAdmin
from apps.blog_demo.admin import CategoryAdmin, PostAdmin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # Tables are managed by Alembic
    # Start listening on each app's PostgreSQL channel
    # app_one does not use realtime — only app_two listens
    await realtime.listen("blog_updates")

    yield

    # --- Shutdown ---
    await realtime.unlisten("blog_updates")
    await engine.dispose()


app = FastAPI(
    title="EversCodeAPI",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Routers ---
app.include_router(app_one_router, prefix="/app-one", tags=["app_one"])
app.include_router(blog_demo_router, prefix="/blog-demo", tags=["blog_demo"])

# --- Admin ---
# SECRET_KEY signs the admin session cookie
admin = Admin(app, engine, base_url="/admin", title="EversCodeAPI Admin", authentication_backend=authentication_backend)
# app_one
admin.add_view(ItemAdmin)

# app_two
admin.add_view(CategoryAdmin)
admin.add_view(PostAdmin)

# --- Static files (create a /static dir if you need to serve assets) ---
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return {"status": "ok", "env": settings.ENV}
