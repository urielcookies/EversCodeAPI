from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
async def test():
    """Health-check endpoint."""
    return {"app": "blog_demo", "status": "ok"}
