import time
import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from core.config import settings

# tells FastAPI to extract the Authorization: Bearer <token> header automatically
security = HTTPBearer()

# In-memory JWKS cache — avoids hitting Clerk on every request
_jwks_cache: dict = {}
_jwks_cached_at: float = 0.0
_JWKS_TTL = 3600  # re-fetch once per hour


async def get_jwks() -> dict:
    global _jwks_cache, _jwks_cached_at
    if _jwks_cache and (time.time() - _jwks_cached_at) < _JWKS_TTL:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cached_at = time.time()
    return _jwks_cache


async def get_current_clerk_user(token=Depends(security)) -> dict:
    # Fetch Clerk's public keys from JWKS URL (cached for 1 hour)
    jwks = await get_jwks()

    # Peek at the token header to find which key was used to sign it
    # JWT header contains a "kid" (key ID) that tells us which public key to use
    unverified_header = jwt.get_unverified_header(token.credentials)

    # Find the matching public key from Clerk's JWKS by comparing kid values
    matching_key = None
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            matching_key = key
            break

    # If no matching key found — try refreshing the cache once (Clerk may have rotated keys)
    if not matching_key:
        global _jwks_cached_at
        _jwks_cached_at = 0.0
        jwks = await get_jwks()
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                matching_key = key
                break

    if not matching_key:
        raise HTTPException(status_code=401, detail="Invalid token: no matching key")

    try:
        # Verify the token signature using the public key
        # If Clerk didn't sign this token this will fail
        payload = jwt.decode(
            token.credentials,
            matching_key,
            algorithms=["RS256"],  # Clerk always uses RS256
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Return the decoded payload, contains sub (clerk_user_id), email, etc.
    return payload
