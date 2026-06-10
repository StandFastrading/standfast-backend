"""HTTP routes for behavioral analytics.

Beta report: one admin-gated, read-only endpoint that summarizes tester
participation, intervention activity, rule-breaking, and journal activity for
the beta window. JSON (full summary + per-user) or CSV (per-user rows only).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from standfast.core.dependencies import AdminUserDep, DbSession
from standfast.features.analytics import service
from standfast.features.analytics.schemas import BetaPhase

router = APIRouter()


@router.get("/beta-report")
async def beta_report(
    _admin: AdminUserDep,
    db: DbSession,
    fmt: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    phase: BetaPhase | None = None,
) -> Response:
    report = await service.build_beta_report(db, from_=from_, to=to, phase=phase)
    if fmt == "csv":
        return Response(
            content=service.report_to_csv(report),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="beta-report.csv"'},
        )
    return JSONResponse(content=report.model_dump(mode="json", by_alias=True))
