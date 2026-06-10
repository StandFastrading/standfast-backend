"""The beta-report endpoint is admin-gated and must reject unauthenticated callers."""

from __future__ import annotations

from fastapi.testclient import TestClient

from standfast.features.analytics import service
from standfast.features.analytics.schemas import (
    BetaReport,
    InterventionActivity,
    JournalActivity,
    Participation,
    PerUserRow,
    ReportWindow,
    RuleBreaking,
    TopViolation,
)


def test_beta_report_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/beta-report").status_code == 401


def test_beta_report_csv_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/beta-report?format=csv").status_code == 401


def _sample_report() -> BetaReport:
    return BetaReport(
        window=ReportWindow(),
        participation=Participation(
            total_testers=2,
            active_testers=1,
            trades_activated=3,
            trades_exited=2,
            trades_open_now=1,
        ),
        intervention_activity=InterventionActivity(
            warnings_triggered=5,
            interventions_total=4,
            revise_trade=2,
            cancel_trade=1,
            continue_anyway=1,
            intervention_response_rate=0.75,
        ),
        rule_breaking=RuleBreaking(
            top_violations=[
                TopViolation(rule_id="setup-approved", label="Setup not in approved list", count=3)
            ],
            in_trade_deviations=2,
            stop_widened_trades=1,
        ),
        journal_activity=JournalActivity(
            daily_reflections=2, distinct_users_reflected=1, trade_reflections=1
        ),
        per_user=[
            PerUserRow(
                user_id=None,
                email="tester@example.com",
                beta_phase="phase_1",
                last_seen_at=None,
                days_active=2,
                trades_activated=3,
                trades_exited=2,
                revise_trade=2,
                cancel_trade=1,
                continue_anyway=1,
                intervention_response_rate=0.75,
                stop_widened_trades=1,
                daily_reflections=2,
            )
        ],
    )


def test_response_rate_zero_when_no_interventions() -> None:
    assert service._response_rate(0, 0, 0) == 0.0


def test_response_rate_rounds() -> None:
    assert service._response_rate(1, 1, 3) == 0.6667


def test_csv_has_header_and_rows() -> None:
    csv_text = service.report_to_csv(_sample_report())
    lines = csv_text.strip().splitlines()
    assert lines[0].split(",") == list(service._CSV_COLUMNS)
    assert "tester@example.com" in lines[1]
    assert len(lines) == 2  # header + one tester row
