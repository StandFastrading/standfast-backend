"""HTTP routes for the broadcasts feature. Thin glue — all logic in service.py."""

from __future__ import annotations

from fastapi import APIRouter

from standfast.core.dependencies import AdminUserDep, DbSession
from standfast.features.broadcasts import service
from standfast.features.broadcasts.schemas import BroadcastRequest, BroadcastResult

router = APIRouter()


@router.post("", response_model=BroadcastResult)
async def send_broadcast(
    payload: BroadcastRequest, _admin: AdminUserDep, db: DbSession
) -> BroadcastResult:
    return await service.send_broadcast(db, payload)
