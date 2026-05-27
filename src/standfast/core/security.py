"""Supabase JWT verification.

Supabase signs session tokens with HS256 using the project's JWT Secret. We verify
that signature on every request, extract the user, and surface it via the
`CurrentUser` FastAPI dependency.

RS256 / JWKS verification is deferred — when Supabase rotates a project to
asymmetric keys, swap `jwt.decode(..., algorithms=["HS256"])` for a JWKS fetch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated Supabase user, derived from a verified JWT."""

    id: str  # Supabase user UUID (sub claim)
    email: str | None
    role: str  # Supabase role, typically "authenticated"
    claims: dict[str, Any]


def _decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
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
    claims = _decode_token(creds.credentials)
    return CurrentUser(
        id=claims["sub"],
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        claims=claims,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
