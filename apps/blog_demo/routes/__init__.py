from fastapi import APIRouter

from .health import router as health_router
from .sse import router as sse_router
from .posts import router as posts_router
from .categories import router as categories_router

router = APIRouter()
router.include_router(health_router)
router.include_router(sse_router)
router.include_router(posts_router, prefix="/posts")
router.include_router(categories_router, prefix="/categories")
