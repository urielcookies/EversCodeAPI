from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from core.config import settings


# Ensure the URL uses the asyncpg driver — Railway injects postgresql:// but we need postgresql+asyncpg://
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(db_url, echo=settings.ENV == "development")

# Session factory — expire_on_commit=False avoids lazy-load errors after commit
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# All models inherit from this Base so metadata.create_all picks them up
Base = declarative_base()


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
