from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin

from core.auth import authentication_backend
from core.config import settings
from core.database import engine
from core.realtime import realtime
from core.security import verify_api_key


from apps.app_one.routes import router as app_one_router
from apps.blog_demo.routes import router as blog_demo_router
from apps.ever_apply.routes import router as ever_apply_router
from apps.ever_apply.scheduler import scheduler

from apps.app_one.admin import ItemAdmin
from apps.blog_demo.admin import CategoryAdmin, PostAdmin
from apps.ever_apply.admin import UserAdmin, JobAdmin, JobMatchAdmin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    # Tables are managed by Alembic
    # Start listening on each app's PostgreSQL channel
    # app_one does not use realtime — only blog_demo listens
    await realtime.listen("blog_updates")
    if settings.EVER_APPLY_SCHEDULER_ENABLED:
        scheduler.start()

    yield

    # --- Shutdown ---
    await realtime.unlisten("blog_updates")
    if settings.EVER_APPLY_SCHEDULER_ENABLED:
        scheduler.shutdown()
    await engine.dispose()


app = FastAPI(
    title="EversCodeAPI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# --- Routers ---
app.include_router(app_one_router, prefix="/app-one", tags=["app_one"])
app.include_router(blog_demo_router, prefix="/blog-demo", tags=["blog_demo"], dependencies=[Depends(verify_api_key)])
app.include_router(ever_apply_router, prefix="/ever-apply", tags=["ever_apply"])

# --- Admin ---
# SECRET_KEY signs the admin session cookie
admin = Admin(app, engine, base_url="/admin", title="EversCodeAPI Admin", authentication_backend=authentication_backend)
# app_one
admin.add_view(ItemAdmin)

# blog_demo
admin.add_view(CategoryAdmin)
admin.add_view(PostAdmin)

# ever_apply
admin.add_view(UserAdmin)
admin.add_view(JobAdmin)
admin.add_view(JobMatchAdmin)

# --- Static files (create a /static dir if you need to serve assets) ---
# app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    return {"status": "ok", "env": settings.ENV}


@app.get("/ever-apply/test", response_class=HTMLResponse)
async def ever_apply_test(request: Request):
    return templates.TemplateResponse(request, name="ever_apply_test.html")
