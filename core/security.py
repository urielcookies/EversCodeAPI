from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key: str = Security(api_key_header)) -> None:
    if api_key != settings.BLOG_DEMO_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
