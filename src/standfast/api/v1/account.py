"""HTTP routes for the account feature. Thin glue — all logic in service.py."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from standfast.core.dependencies import CurrentUserDep, DbSession
from standfast.features.account import service
from standfast.features.account.schemas import UserProfileRead, UserProfileUpdate

router = APIRouter()


@router.get("/me", response_model=UserProfileRead)
async def read_me(user: CurrentUserDep, db: DbSession) -> UserProfileRead:
    profile = await service.get_or_create_profile(db, UUID(user.id))
    return UserProfileRead.model_validate(profile)


@router.patch("/me", response_model=UserProfileRead)
async def update_me(
    patch: UserProfileUpdate, user: CurrentUserDep, db: DbSession
) -> UserProfileRead:
    profile = await service.update_profile(db, UUID(user.id), patch)
    return UserProfileRead.model_validate(profile)
