from fastapi import APIRouter

from .ping import router as ping_router
from .users import router as users_router
from .matches import router as matches_router
from .jobs import router as jobs_router
from .admin import router as admin_router
from .webhooks import router as webhooks_router

router = APIRouter()
router.include_router(ping_router)
router.include_router(users_router, prefix="/users")
router.include_router(matches_router, prefix="/matches")
router.include_router(jobs_router, prefix="/jobs")
router.include_router(admin_router, prefix="/admin")
router.include_router(webhooks_router, prefix="/webhooks")
