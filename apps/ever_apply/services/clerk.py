import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from core.config import settings

# tells FastAPI to extract the Authorization: Bearer <token> header automatically
security = HTTPBearer()

async def get_jwks():
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        return response.json()

async def get_current_clerk_user(token=Depends(security)) -> dict:
    jwks = await get_jwks()

    unverified_header = jwt.get_unverified_header(token.credentials)

    public_key = None
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break

    if not public_key:
        raise HTTPException(status_code=401, detail="Invalid token: no matching key")

    try:
        payload = jwt.decode(
            token.credentials,
            public_key,
            algorithms=["RS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload
