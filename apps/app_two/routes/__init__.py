from fastapi import APIRouter

from .health import router as health_router
from .sse import router as sse_router

router = APIRouter()
router.include_router(health_router)
router.include_router(sse_router)
