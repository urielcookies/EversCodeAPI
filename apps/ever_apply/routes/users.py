from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from apps.ever_apply.models import User
from apps.ever_apply.schemas import UserRead, UserPreferenceRead, UserPreferencesUpdate
from apps.ever_apply.services.clerk import get_current_clerk_user
from apps.ever_apply.services.resume import upload_resume, delete_resume, extract_text, parse_resume

router = APIRouter()


# POST /users/me
# Creates user on first login, returns existing user on subsequent logins
@router.post("/me", response_model=UserRead)
async def get_or_create_user(
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    # Try to fetch existing user by Clerk ID
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()

    # First login — create the record
    if not user:
        user = User(
            clerk_user_id=clerk_user["sub"],
            email=clerk_user.get("email", ""),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


# GET /users/preferences
@router.get("/preferences", response_model=UserPreferenceRead)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user or not user.preferences:
        raise HTTPException(status_code=404, detail="Preferences not set")
    return UserPreferenceRead(**user.preferences)


# PUT /users/preferences
@router.put("/preferences", response_model=UserPreferenceRead)
async def update_preferences(
    body: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Merge new values into existing preferences
    current = user.preferences or {}
    updates = body.model_dump(exclude_unset=True)
    user.preferences = {**current, **updates}

    await db.commit()
    await db.refresh(user)
    return UserPreferenceRead(**user.preferences)


# POST /users/resume
# Upload resume PDF → store in R2 → extract text → parse with DeepSeek → save to DB
@router.post("/resume", response_model=UserRead)
async def upload_user_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    clerk_user: dict = Depends(get_current_clerk_user),
):
    # Fetch user
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Call /users/me first.")

    # Read file bytes once — reuse for both upload and text extraction
    file_bytes = await file.read()

    # 1. Delete old resume from R2 if one exists
    if user.resume_url:
        await delete_resume(user.resume_url)

    # 2. Upload to R2
    resume_url = await upload_resume(file_bytes, file.filename, clerk_user["sub"])

    # 3. Extract text from PDF
    text = extract_text(file_bytes)

    # 4. Parse with DeepSeek
    parsed_data = await parse_resume(text)

    # 4. Save to DB
    user.resume_url = resume_url
    user.parsed_data = parsed_data
    await db.commit()
    await db.refresh(user)

    return user
