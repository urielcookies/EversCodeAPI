from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
async def test():
    """ping-check endpoint."""
    return {"app": "ever_apply", "status": "ok"}
