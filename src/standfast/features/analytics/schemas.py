"""Pydantic DTOs for the beta report — the admin-facing contract.

Mirrors the approved build spec exactly: one summary object with four sections
plus per-user rows. Read-only; no writes anywhere in this feature.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BetaPhase = Literal["phase_1", "phase_2"]


class ReportWindow(BaseModel):
    """Echo of the requested window/filters (null = unbounded / all phases)."""

    model_config = ConfigDict(populate_by_name=True)

    # Python name `from_` (init arg) with the wire name `from` (a reserved word).
    from_: datetime | None = Field(
        default=None, validation_alias="from", serialization_alias="from"
    )
    to: datetime | None = None
    phase: BetaPhase | None = None


class Participation(BaseModel):
    total_testers: int
    active_testers: int
    trades_activated: int
    trades_exited: int
    trades_open_now: int


class InterventionActivity(BaseModel):
    warnings_triggered: int
    interventions_total: int
    revise_trade: int
    cancel_trade: int
    continue_anyway: int
    intervention_response_rate: float


class TopViolation(BaseModel):
    rule_id: str
    label: str | None
    count: int


class RuleBreaking(BaseModel):
    top_violations: list[TopViolation]
    in_trade_deviations: int
    stop_widened_trades: int


class JournalActivity(BaseModel):
    daily_reflections: int
    distinct_users_reflected: int
    trade_reflections: int


class PerUserRow(BaseModel):
    user_id: UUID | None
    email: str
    beta_phase: BetaPhase
    last_seen_at: datetime | None
    days_active: int
    trades_activated: int
    trades_exited: int
    revise_trade: int
    cancel_trade: int
    continue_anyway: int
    intervention_response_rate: float
    stop_widened_trades: int
    daily_reflections: int


class BetaReport(BaseModel):
    window: ReportWindow
    participation: Participation
    intervention_activity: InterventionActivity
    rule_breaking: RuleBreaking
    journal_activity: JournalActivity
    per_user: list[PerUserRow]
