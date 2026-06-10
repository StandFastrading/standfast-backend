"""Supabase admin client.

We verify JWTs from the frontend in [core/security.py]. For admin actions —
enumerating users, signed URLs for Storage, password resets — call this module.
Uses `httpx.AsyncClient` against the Supabase REST/Auth API with the
service-role key as the bearer token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from standfast.core.config import get_settings
from standfast.core.errors import AppError


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None


@dataclass(frozen=True)
class SessionTokens:
    """A minted Supabase session, handed to the frontend to set client-side."""

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str


def _admin_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }


async def get_auth_user(user_id: str) -> AuthUser | None:
    """Single-user lookup via the Auth Admin API. Returns None if not found."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.get(
            f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
        )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    body = response.json()
    return AuthUser(id=str(body["id"]), email=body.get("email"))


async def list_auth_users(*, per_page: int = 1000) -> list[AuthUser]:
    """Paginated read of every user in Supabase Auth.

    Supabase caps per_page at 1000. For multi-thousand-user lists this walks
    pages serially; that's fine for current scale and avoids hammering the API.
    """
    settings = get_settings()
    users: list[AuthUser] = []
    page = 1
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }

    async with httpx.AsyncClient(timeout=15.0) as http:
        while True:
            response = await http.get(
                f"{settings.supabase_url}/auth/v1/admin/users",
                params={"page": page, "per_page": per_page},
                headers=headers,
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            batch = body.get("users", [])
            if not batch:
                break
            for u in batch:
                users.append(AuthUser(id=str(u["id"]), email=u.get("email")))
            if len(batch) < per_page:
                break
            page += 1

    return users


async def create_auth_user(
    *, email: str, user_metadata: dict[str, Any]
) -> AuthUser | None:
    """Create a confirmed, password-less auth user via the Admin API.

    Used for the hidden beta-tester accounts: `email_confirm=True` skips the
    confirmation email, and the metadata is copied into `profiles` by the
    `handle_new_user` trigger. Returns None if the user already exists
    (idempotent — callers then mint a session for the existing user).
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as http:
        response = await http.post(
            f"{settings.supabase_url}/auth/v1/admin/users",
            headers=_admin_headers(),
            json={
                "email": email,
                "email_confirm": True,
                "user_metadata": user_metadata,
            },
        )
    if response.status_code in (409, 422):
        return None  # already registered
    response.raise_for_status()
    body = response.json()
    return AuthUser(id=str(body["id"]), email=body.get("email"))


async def mint_session(email: str) -> SessionTokens:
    """Issue a session for an existing user without a password or email round-trip.

    Generates a magic link server-side (no email is sent) and immediately
    verifies its token to exchange it for access/refresh tokens.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as http:
        link = await http.post(
            f"{settings.supabase_url}/auth/v1/admin/generate_link",
            headers=_admin_headers(),
            json={"type": "magiclink", "email": email},
        )
        link.raise_for_status()
        link_body: dict[str, Any] = link.json()
        hashed_token = link_body.get("hashed_token") or link_body.get(
            "properties", {}
        ).get("hashed_token")
        if not hashed_token:
            raise AppError(
                "could not generate beta session link", code="beta_link_failed"
            )

        verify = await http.post(
            f"{settings.supabase_url}/auth/v1/verify",
            headers={"apikey": settings.supabase_service_role_key},
            json={"type": "magiclink", "token_hash": hashed_token},
        )
        verify.raise_for_status()
        verify_body: dict[str, Any] = verify.json()

    access_token = verify_body.get("access_token")
    refresh_token = verify_body.get("refresh_token")
    user = verify_body.get("user") or {}
    user_id = user.get("id")
    if not access_token or not refresh_token or not user_id:
        raise AppError("could not mint beta session", code="beta_session_failed")

    return SessionTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(verify_body.get("expires_in", 3600)),
        user_id=str(user_id),
    )
