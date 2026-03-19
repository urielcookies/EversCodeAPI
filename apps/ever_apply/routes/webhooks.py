import logging
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from svix.webhooks import Webhook, WebhookVerificationError

from core.config import settings
from core.database import get_db
from fastapi import Depends
from apps.ever_apply.models import User, JobMatch
from apps.ever_apply.services.resume import delete_resume

logger = logging.getLogger("ever_apply.webhooks")

router = APIRouter()


# POST /webhooks/clerk
# Handles Clerk webhook events — currently only user.deleted
@router.post("/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    headers = dict(request.headers)

    # Verify the webhook signature using the Svix signing secret
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        event = wh.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type")
    if event_type != "user.deleted":
        return {"received": True}

    clerk_user_id = event.get("data", {}).get("id")
    if not clerk_user_id:
        raise HTTPException(status_code=400, detail="Missing user ID in webhook payload")

    # Look up the user
    result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        # Already gone or never created — nothing to do
        return {"received": True}

    # Delete resume from R2 if one exists
    if user.resume_url:
        try:
            await delete_resume(user.resume_url)
        except Exception:
            logger.exception(f"Failed to delete R2 resume for user {user.id}")

    # Delete matches first (FK constraint)
    await db.execute(delete(JobMatch).where(JobMatch.user_id == user.id))

    # Delete user record
    await db.delete(user)
    await db.commit()

    logger.info(f"clerk_webhook: deleted user {user.id} ({clerk_user_id}) and their data")
    return {"received": True}
