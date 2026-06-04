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


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None


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
