from fastapi import Header, HTTPException, Query
from jose import jwt, JWTError
import httpx
import time

from app.config import settings


_jwks_cache = {
    "keys": None,
    "fetched_at": 0
}

CACHE_TTL_SECONDS = 600


async def get_jwks():
    now = time.time()

    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < CACHE_TTL_SECONDS:
        return _jwks_cache["keys"]

    async with httpx.AsyncClient() as client:
        response = await client.get(settings.jwks_uri, timeout=5)
        response.raise_for_status()
        data = response.json()

    _jwks_cache["keys"] = data["keys"]
    _jwks_cache["fetched_at"] = now

    return _jwks_cache["keys"]


async def require_auth(authorization: str = Header(default="")):
    if settings.skip_auth:
        return {
            "sub": "local-user-id",
            "email": "local-user@ubicatec.ac.cr",
            "role": "USER"
        }

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")

    token = authorization.replace("Bearer ", "")

    try:
        keys = await get_jwks()
        payload = jwt.decode(
            token,
            keys,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer
        )
        return payload
    except JWTError as error:
        raise HTTPException(status_code=401, detail=f"Token inválido: {error}")


async def verify_token_ws(token: str = Query(default="")):
    if settings.skip_auth:
        return {
            "sub": "local-user-id",
            "email": "local-user@ubicatec.ac.cr",
            "role": "USER"
        }

    if not token:
        return None

    try:
        keys = await get_jwks()
        payload = jwt.decode(
            token,
            keys,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer
        )
        return payload
    except JWTError:
        return None