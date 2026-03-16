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
    # Fetch Clerk's public keys from JWKS URL
    jwks = await get_jwks()

    # Peek at the token header to find which key was used to sign it
    # JWT header contains a "kid" (key ID) that tells us which public key to use
    unverified_header = jwt.get_unverified_header(token.credentials)

    # Find the matching public key from Clerk's JWKS by comparing kid values
    public_key = None
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            # Convert the raw JWK format into an RSA public key object
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break

    # If no matching key found the token is fake or from a different app
    if not public_key:
        raise HTTPException(status_code=401, detail="Invalid token: no matching key")

    try:
        # Verify the token signature using the public key
        # If Clerk didn't sign this token this will fail
        payload = jwt.decode(
            token.credentials,
            public_key,
            algorithms=["RS256"],  # Clerk always uses RS256
        )
    except jwt.ExpiredSignatureError:
        # Token is real but has expired, user needs to log in again
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        # Token is malformed, tampered with, or otherwise invalid
        raise HTTPException(status_code=401, detail="Invalid token")

    # Return the decoded payload, contains sub (clerk_user_id), email, etc.
    return payload
