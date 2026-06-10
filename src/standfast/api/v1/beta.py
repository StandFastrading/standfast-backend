"""HTTP routes for beta entry. Thin glue — all logic in service.py.

This endpoint is intentionally unauthenticated: it IS the entry point. It
validates email + access code against the approved tester list and returns a
minted Supabase session for the frontend to set client-side.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from standfast.core.dependencies import AdminUserDep, DbSession
from standfast.features.beta import service
from standfast.features.beta.schemas import (
    BetaEntryRequest,
    BetaEntryResponse,
    BetaTesterCreate,
    BetaTesterRead,
    BetaTesterUpdate,
)

router = APIRouter()


@router.post("/entry", response_model=BetaEntryResponse)
async def beta_entry(payload: BetaEntryRequest, db: DbSession) -> BetaEntryResponse:
    return await service.enter_beta(
        db, email=payload.email, access_code=payload.access_code
    )


# --- Admin: tester management (gated by the ADMIN_EMAILS allowlist) ----------


@router.get("/admin/testers", response_model=list[BetaTesterRead])
async def list_beta_testers(
    _admin: AdminUserDep, db: DbSession
) -> list[BetaTesterRead]:
    return await service.list_testers(db)


@router.post("/admin/testers", response_model=BetaTesterRead, status_code=201)
async def create_beta_tester(
    payload: BetaTesterCreate, _admin: AdminUserDep, db: DbSession
) -> BetaTesterRead:
    return await service.create_tester(db, payload)


@router.patch("/admin/testers/{tester_id}", response_model=BetaTesterRead)
async def update_beta_tester(
    tester_id: UUID,
    payload: BetaTesterUpdate,
    _admin: AdminUserDep,
    db: DbSession,
) -> BetaTesterRead:
    return await service.update_tester(db, tester_id, payload)
