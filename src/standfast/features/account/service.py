"""Account business logic. Callable from routers OR background tasks — no FastAPI imports."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from . import repository
from .models import UserProfile
from .schemas import UserProfileUpdate


async def get_or_create_profile(session: AsyncSession, user_id: UUID) -> UserProfile:
    """Look up the profile; create an empty row on first call."""
    existing = await repository.find_by_user_id(session, user_id)
    if existing is not None:
        return existing
    return await repository.insert(session, UserProfile(user_id=user_id))


async def update_profile(
    session: AsyncSession, user_id: UUID, patch: UserProfileUpdate
) -> UserProfile:
    profile = await get_or_create_profile(session, user_id)
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await session.flush()
    return profile
