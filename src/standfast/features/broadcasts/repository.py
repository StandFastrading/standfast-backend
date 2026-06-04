"""Broadcasts DB queries. Pure data access — no business logic, no HTTP."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import EmailUnsubscribe


async def list_unsubscribed_user_ids(session: AsyncSession) -> set[UUID]:
    result = await session.execute(select(EmailUnsubscribe.user_id))
    return {row for row in result.scalars()}


async def upsert_unsubscribe(session: AsyncSession, *, user_id: UUID, email: str) -> None:
    """Idempotent — repeated clicks on the unsubscribe link are no-ops."""
    stmt = (
        pg_insert(EmailUnsubscribe)
        .values(user_id=user_id, email=email)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.execute(stmt)
