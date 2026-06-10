"""Supabase JWT verification.

Supabase signs session tokens with asymmetric keys (ES256, possibly RS256). We
verify each token against the project's published JWKS — the public keys at
`{SUPABASE_URL}/auth/v1/.well-known/jwks.json` — extract the user, and surface
it via the `CurrentUser` dependency.

`PyJWKClient` fetches + caches the JWKS and selects the signing key by the
token's `kid`, so key rotation is handled automatically and verification never
depends on the legacy HS256 shared secret. Algorithms are restricted to the
asymmetric set (never HS256 / none) to avoid algorithm-confusion attacks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

# Asymmetric only — never HS256 or "none".
_ALLOWED_ALGORITHMS = ["ES256", "RS256"]


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated Supabase user, derived from a verified JWT."""

    id: str  # Supabase user UUID (sub claim)
    email: str | None
    role: str  # Supabase role, typically "authenticated"
    claims: dict[str, Any]


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    settings = get_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


async def _decode_token(token: str) -> dict[str, Any]:
    client = _jwk_client()
    try:
        # JWKS fetch can hit the network on a cache miss — keep it off the loop.
        signing_key = await asyncio.to_thread(client.get_signing_key_from_jwt, token)
    except PyJWKClientError as e:
        # Unknown `kid` or JWKS endpoint unreachable — we can't verify right now.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="auth keys unavailable"
        ) from e

    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALLOWED_ALGORITHMS,
            audience="authenticated",
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from e


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    claims = await _decode_token(creds.credentials)
    return CurrentUser(
        id=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        claims=claims,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
