"""Beta entry business logic. Callable from routers OR tasks — no FastAPI imports.

Flow for `enter_beta` (Path A: hidden Supabase Auth):
  1. Look up the email in the approved `beta_testers` list (gate).
  2. Reject if the tester is inactive.
  3. Reject if the submitted code != the active code for the tester's phase.
  4. On first entry, create one hidden, confirmed auth user (the trigger tags
     `profiles` with beta_phase / signup_date / access_code_used).
  5. Mint a session (no password, no email) and persist the tester's user_id so
     every future visit resolves the same auth user — keeping all of a tester's
     data connected over time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from standfast.core.errors import ConflictError, ForbiddenError, NotFoundError
from standfast.integrations import supabase

from . import repository
from .models import BetaTester
from .schemas import (
    BetaEntryResponse,
    BetaTesterCreate,
    BetaTesterRead,
    BetaTesterUpdate,
)


async def enter_beta(
    session: AsyncSession, *, email: str, access_code: str
) -> BetaEntryResponse:
    tester = await repository.find_tester_by_email(session, email)
    if tester is None:
        raise ForbiddenError("not an approved beta tester", code="not_approved")
    if not tester.is_active:
        raise ForbiddenError(
            "beta access is inactive for this tester", code="tester_inactive"
        )

    expected_code = await repository.get_active_code_for_phase(session, tester.beta_phase)
    if expected_code is None or access_code != expected_code:
        raise ForbiddenError(
            "access code does not match your beta phase", code="bad_access_code"
        )

    is_new = tester.user_id is None
    if is_new:
        # Idempotent: returns None if the user already exists (e.g. a prior
        # entry created the auth user but crashed before saving user_id).
        await supabase.create_auth_user(
            email=email,
            user_metadata={
                "beta_phase": tester.beta_phase,
                "access_code_used": access_code,
            },
        )

    tokens = await supabase.mint_session(email)
    tester.user_id = UUID(tokens.user_id)
    tester.last_seen_at = datetime.now(UTC)
    await session.flush()

    return BetaEntryResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        beta_phase=tester.beta_phase,  # type: ignore[arg-type]
        is_new=is_new,
    )


# --- Admin tester management -------------------------------------------------


async def list_testers(session: AsyncSession) -> list[BetaTesterRead]:
    testers = await repository.list_testers(session)
    return [BetaTesterRead.model_validate(t) for t in testers]


async def create_tester(
    session: AsyncSession, payload: BetaTesterCreate
) -> BetaTesterRead:
    # payload.email is already normalized (lower/stripped) by the schema.
    existing = await repository.find_tester_by_email(session, payload.email)
    if existing is not None:
        raise ConflictError(
            f"a beta tester with email {payload.email} already exists"
        )
    tester = BetaTester(
        id=uuid4(),
        email=payload.email,
        beta_phase=payload.beta_phase,
        is_active=payload.is_active,
        user_id=None,
        created_at=datetime.now(UTC),
        last_seen_at=None,
    )
    saved = await repository.insert_tester(session, tester)
    return BetaTesterRead.model_validate(saved)


async def update_tester(
    session: AsyncSession, tester_id: UUID, payload: BetaTesterUpdate
) -> BetaTesterRead:
    tester = await repository.get_tester_by_id(session, tester_id)
    if tester is None:
        raise NotFoundError("beta tester not found")
    if payload.is_active is not None:
        tester.is_active = payload.is_active
    if payload.beta_phase is not None:
        tester.beta_phase = payload.beta_phase
    await session.flush()
    return BetaTesterRead.model_validate(tester)
