"""Account DB queries. Pure data access — no business logic, no HTTP."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserProfile


async def find_by_user_id(session: AsyncSession, user_id: UUID) -> UserProfile | None:
    result = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def insert(session: AsyncSession, profile: UserProfile) -> UserProfile:
    session.add(profile)
    await session.flush()
    return profile
