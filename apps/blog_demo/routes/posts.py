import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from apps.blog_demo.models import Post
from apps.blog_demo.schemas import PostCreate, PostRead, PostUpdate

router = APIRouter()

CHANNEL = "blog_updates"


@router.get("", response_model=list[PostRead])
async def list_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).options(selectinload(Post.category)))
    return result.scalars().all()


@router.get("/{post_id}", response_model=PostRead)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.category))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("", response_model=PostRead, status_code=201)
async def create_post(body: PostCreate, db: AsyncSession = Depends(get_db)):
    post = Post(**body.model_dump())
    db.add(post)
    await db.commit()
    await db.refresh(post)

    if post.published:
        payload = json.dumps({"event": "post_published", "title": post.title, "slug": post.slug})
        await db.execute(text("SELECT pg_notify(:channel, :payload)"), {"channel": CHANNEL, "payload": payload})
        await db.commit()

    # Re-fetch with relationship loaded for response
    result = await db.execute(
        select(Post).where(Post.id == post.id).options(selectinload(Post.category))
    )
    return result.scalar_one()


@router.patch("/{post_id}", response_model=PostRead)
async def update_post(post_id: int, body: PostUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post)

    result = await db.execute(
        select(Post).where(Post.id == post.id).options(selectinload(Post.category))
    )
    return result.scalar_one()


@router.delete("/{post_id}", status_code=204)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await db.delete(post)
    await db.commit()
