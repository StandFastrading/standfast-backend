"""Beta-report business logic. Assembles the report and serializes CSV.

Callable from routers OR tasks — no FastAPI imports. Pure read path.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from . import repository
from .schemas import (
    BetaPhase,
    BetaReport,
    InterventionActivity,
    JournalActivity,
    Participation,
    PerUserRow,
    ReportWindow,
    RuleBreaking,
    TopViolation,
)

# Unbounded window sentinels — used when the caller omits from/to. Wide enough
# to cover all real data without dragging NULL-handling into every query.
_FAR_PAST = datetime(1970, 1, 1, tzinfo=UTC)
_FAR_FUTURE = datetime(2999, 1, 1, tzinfo=UTC)

# Per-user CSV column order (matches the approved spec, section 6).
_CSV_COLUMNS = (
    "user_id",
    "email",
    "beta_phase",
    "last_seen_at",
    "days_active",
    "trades_activated",
    "trades_exited",
    "revise_trade",
    "cancel_trade",
    "continue_anyway",
    "intervention_response_rate",
    "stop_widened_trades",
    "daily_reflections",
)


def _response_rate(revise: int, cancel: int, total: int) -> float:
    """(revise + cancel) / total interventions. 0.0 when there are none."""
    if total <= 0:
        return 0.0
    return round((revise + cancel) / total, 4)


async def build_beta_report(
    session: AsyncSession,
    *,
    from_: datetime | None,
    to: datetime | None,
    phase: BetaPhase | None,
) -> BetaReport:
    params: dict[str, Any] = {
        "from_ts": from_ or _FAR_PAST,
        "to_ts": to or _FAR_FUTURE,
        "phase": phase,
    }

    trades = await repository.trade_counts(session, params)
    participation = Participation(
        total_testers=await repository.total_testers(session, params),
        active_testers=await repository.active_testers(session, params),
        trades_activated=trades["trades_activated"],
        trades_exited=trades["trades_exited"],
        trades_open_now=trades["trades_open_now"],
    )

    ic = await repository.intervention_counts(session, params)
    intervention_activity = InterventionActivity(
        warnings_triggered=await repository.warnings_triggered(session, params),
        interventions_total=ic["interventions_total"],
        revise_trade=ic["revise_trade"],
        cancel_trade=ic["cancel_trade"],
        continue_anyway=ic["continue_anyway"],
        intervention_response_rate=_response_rate(
            ic["revise_trade"], ic["cancel_trade"], ic["interventions_total"]
        ),
    )

    rule_breaking = RuleBreaking(
        top_violations=[
            TopViolation(**v) for v in await repository.top_violations(session, params)
        ],
        in_trade_deviations=await repository.in_trade_deviations(session, params),
        stop_widened_trades=await repository.stop_widened_trades(session, params),
    )

    jc = await repository.journal_counts(session, params)
    journal_activity = JournalActivity(
        daily_reflections=jc["daily_reflections"],
        distinct_users_reflected=jc["distinct_users_reflected"],
        trade_reflections=jc["trade_reflections"],
    )

    per_user = [
        PerUserRow(
            user_id=r["user_id"],
            email=r["email"],
            beta_phase=r["beta_phase"],
            last_seen_at=r["last_seen_at"],
            days_active=r["days_active"],
            trades_activated=r["trades_activated"],
            trades_exited=r["trades_exited"],
            revise_trade=r["revise_trade"],
            cancel_trade=r["cancel_trade"],
            continue_anyway=r["continue_anyway"],
            intervention_response_rate=_response_rate(
                r["revise_trade"],
                r["cancel_trade"],
                r["revise_trade"] + r["cancel_trade"] + r["continue_anyway"],
            ),
            stop_widened_trades=r["stop_widened_trades"],
            daily_reflections=r["daily_reflections"],
        )
        for r in await repository.per_user_rows(session, params)
    ]

    return BetaReport(
        window=ReportWindow(from_=from_, to=to, phase=phase),
        participation=participation,
        intervention_activity=intervention_activity,
        rule_breaking=rule_breaking,
        journal_activity=journal_activity,
        per_user=per_user,
    )


def report_to_csv(report: BetaReport) -> str:
    """Serialize the per-user rows to CSV (the spreadsheet artifact)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS)
    writer.writeheader()
    for row in report.per_user:
        data = row.model_dump(mode="json")
        writer.writerow({col: data[col] for col in _CSV_COLUMNS})
    return buf.getvalue()
