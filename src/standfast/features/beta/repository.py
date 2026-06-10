"""Beta DB queries. Pure data access — no business logic, no HTTP."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BetaAccessCode, BetaTester


async def list_testers(session: AsyncSession) -> list[BetaTester]:
    result = await session.execute(
        select(BetaTester).order_by(BetaTester.created_at.desc())
    )
    return list(result.scalars().all())


async def get_tester_by_id(
    session: AsyncSession, tester_id: UUID
) -> BetaTester | None:
    result = await session.execute(
        select(BetaTester).where(BetaTester.id == tester_id)
    )
    return result.scalar_one_or_none()


async def insert_tester(session: AsyncSession, tester: BetaTester) -> BetaTester:
    session.add(tester)
    await session.flush()
    return tester


async def find_tester_by_email(session: AsyncSession, email: str) -> BetaTester | None:
    # email is citext in Postgres, so the comparison is case-insensitive.
    result = await session.execute(select(BetaTester).where(BetaTester.email == email))
    return result.scalar_one_or_none()


async def get_active_code_for_phase(session: AsyncSession, beta_phase: str) -> str | None:
    result = await session.execute(
        select(BetaAccessCode.code).where(
            BetaAccessCode.beta_phase == beta_phase,
            BetaAccessCode.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
