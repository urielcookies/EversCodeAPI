from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
async def test():
    """Health-check endpoint."""
    return {"app": "app_two", "status": "ok"}
