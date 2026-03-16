from fastapi import APIRouter, Depends
from apps.ever_apply.services.clerk import get_current_clerk_user

router = APIRouter()

@router.get("/ping")
async def ping(user=Depends(get_current_clerk_user)):
    """ping-check endpoint."""
    return {"app": "ever_apply", "status": "ok", "clerk_user_id": user["sub"]}
