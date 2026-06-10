"""Beta-report DB queries. Pure read-only aggregates — no business logic, no HTTP.

Every query is scoped to approved beta testers (via the `_BETA_USERS` subquery)
and to the [from_ts, to_ts) half-open window. The backend connects as the
Postgres role and bypasses RLS, so these tables (owned by the web layer) are
readable directly. Nothing here writes.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Stable rule-id vocabulary from the web validation engine
# (standfast-web/src/lib/validation/trade-validation-engine.ts RULE_IDS).
# Dynamic in-trade deviation entries use `dev-*` ids and are excluded here;
# they are counted separately as `in_trade_deviations`.
STABLE_RULE_IDS = (
    "stop-entered",
    "plan-written",
    "setup-approved",
    "risk-limit",
    "daily-loss",
    "daily-trade-count",
    "red-trades",
    "consecutive-losses",
    "cooldown",
    "reward-risk",
)

# Approved beta testers who have entered (have a user_id), optionally filtered
# to one phase. Referenced as a subquery so every metric counts tester activity
# only. `:phase` is a bound param; never string-interpolated.
_BETA_USERS = (
    "select user_id from beta_testers "
    "where user_id is not null "
    "and (cast(:phase as text) is null or beta_phase::text = cast(:phase as text))"
)

_WINDOW = '"timestamp" >= :from_ts and "timestamp" < :to_ts'


async def total_testers(session: AsyncSession, params: dict[str, Any]) -> int:
    sql = text(
        "select count(*) from beta_testers "
        "where is_active = true "
        "and (cast(:phase as text) is null or beta_phase::text = cast(:phase as text))"
    )
    return int((await session.execute(sql, params)).scalar_one())


async def active_testers(session: AsyncSession, params: dict[str, Any]) -> int:
    sql = text(
        f"select count(distinct user_id) from behavior_events "
        f"where {_WINDOW} and user_id in ({_BETA_USERS})"
    )
    return int((await session.execute(sql, params)).scalar_one())


async def trade_counts(session: AsyncSession, params: dict[str, Any]) -> dict[str, int]:
    sql = text(
        f"select "
        f"  count(*) filter (where activated_at >= :from_ts and activated_at < :to_ts) "
        f"    as trades_activated, "
        f"  count(*) filter (where status = 'closed' "
        f"    and closed_at >= :from_ts and closed_at < :to_ts) as trades_exited, "
        f"  count(*) filter (where status = 'active') as trades_open_now "
        f"from trades where user_id in ({_BETA_USERS})"
    )
    row = (await session.execute(sql, params)).mappings().one()
    return {k: int(v) for k, v in row.items()}


async def warnings_triggered(session: AsyncSession, params: dict[str, Any]) -> int:
    sql = text(
        f"select count(*) from behavior_events "
        f"where severity in ('warning', 'fail') "
        f"and {_WINDOW} and user_id in ({_BETA_USERS})"
    )
    return int((await session.execute(sql, params)).scalar_one())


async def intervention_counts(
    session: AsyncSession, params: dict[str, Any]
) -> dict[str, int]:
    sql = text(
        f"select "
        f"  count(*) as interventions_total, "
        f"  count(*) filter (where decision = 'revise_trade') as revise_trade, "
        f"  count(*) filter (where decision = 'cancel_trade') as cancel_trade, "
        f"  count(*) filter (where decision = 'continue_anyway') as continue_anyway "
        f"from interventions "
        f"where {_WINDOW} and user_id in ({_BETA_USERS})"
    )
    row = (await session.execute(sql, params)).mappings().one()
    return {k: int(v) for k, v in row.items()}


async def top_violations(
    session: AsyncSession, params: dict[str, Any]
) -> list[dict[str, Any]]:
    # Group by the stable rule id; label can vary per id so take a representative.
    id_list = ", ".join(f"'{rid}'" for rid in STABLE_RULE_IDS)
    sql = text(
        f"select elem->>'id' as rule_id, max(elem->>'label') as label, "
        f"  count(*) as count "
        f"from behavior_events, lateral jsonb_array_elements(triggered_rules) elem "
        f"where {_WINDOW} and user_id in ({_BETA_USERS}) "
        f"  and elem->>'id' in ({id_list}) "
        f"group by 1 order by count desc, rule_id limit 10"
    )
    rows = (await session.execute(sql, params)).mappings().all()
    return [
        {"rule_id": r["rule_id"], "label": r["label"], "count": int(r["count"])}
        for r in rows
    ]


async def in_trade_deviations(session: AsyncSession, params: dict[str, Any]) -> int:
    # Aggregate count of dynamic `dev-*` deviation entries; never itemized.
    sql = text(
        f"select count(*) "
        f"from behavior_events, lateral jsonb_array_elements(triggered_rules) elem "
        f"where {_WINDOW} and user_id in ({_BETA_USERS}) "
        f"and elem->>'id' like 'dev-%'"
    )
    return int((await session.execute(sql, params)).scalar_one())


async def stop_widened_trades(session: AsyncSession, params: dict[str, Any]) -> int:
    # Trade-level proxy: stop ended wider than baseline (direction-aware).
    sql = text(
        f"select count(*) from trades "
        f"where user_id in ({_BETA_USERS}) "
        f"  and stop_price is not null and current_stop_price is not null "
        f"  and activated_at >= :from_ts and activated_at < :to_ts "
        f"  and ((direction = 'Long' and current_stop_price < stop_price) "
        f"    or (direction = 'Short' and current_stop_price > stop_price))"
    )
    return int((await session.execute(sql, params)).scalar_one())


async def journal_counts(
    session: AsyncSession, params: dict[str, Any]
) -> dict[str, int]:
    daily = text(
        f"select count(*) as daily_reflections, "
        f"  count(distinct user_id) as distinct_users_reflected "
        f"from daily_reflections "
        f"where saved_at >= :from_ts and saved_at < :to_ts "
        f"and user_id in ({_BETA_USERS})"
    )
    trade = text(
        f"select count(*) from trade_reflections "
        f"where saved_at >= :from_ts and saved_at < :to_ts "
        f"and user_id in ({_BETA_USERS})"
    )
    drow = (await session.execute(daily, params)).mappings().one()
    trade_reflections = (await session.execute(trade, params)).scalar_one()
    return {
        "daily_reflections": int(drow["daily_reflections"]),
        "distinct_users_reflected": int(drow["distinct_users_reflected"]),
        "trade_reflections": int(trade_reflections),
    }


async def per_user_rows(
    session: AsyncSession, params: dict[str, Any]
) -> list[dict[str, Any]]:
    sql = text(
        "select "
        "  bt.user_id, bt.email, bt.beta_phase::text as beta_phase, bt.last_seen_at, "
        "  (select count(distinct be.trading_date) from behavior_events be "
        "     where be.user_id = bt.user_id "
        "       and be.\"timestamp\" >= :from_ts and be.\"timestamp\" < :to_ts) "
        "    as days_active, "
        "  (select count(*) from trades t where t.user_id = bt.user_id "
        "     and t.activated_at >= :from_ts and t.activated_at < :to_ts) "
        "    as trades_activated, "
        "  (select count(*) from trades t where t.user_id = bt.user_id "
        "     and t.status = 'closed' "
        "     and t.closed_at >= :from_ts and t.closed_at < :to_ts) as trades_exited, "
        "  (select count(*) from interventions i where i.user_id = bt.user_id "
        "     and i.decision = 'revise_trade' "
        "     and i.\"timestamp\" >= :from_ts and i.\"timestamp\" < :to_ts) "
        "    as revise_trade, "
        "  (select count(*) from interventions i where i.user_id = bt.user_id "
        "     and i.decision = 'cancel_trade' "
        "     and i.\"timestamp\" >= :from_ts and i.\"timestamp\" < :to_ts) "
        "    as cancel_trade, "
        "  (select count(*) from interventions i where i.user_id = bt.user_id "
        "     and i.decision = 'continue_anyway' "
        "     and i.\"timestamp\" >= :from_ts and i.\"timestamp\" < :to_ts) "
        "    as continue_anyway, "
        "  (select count(*) from trades t where t.user_id = bt.user_id "
        "     and t.stop_price is not null and t.current_stop_price is not null "
        "     and t.activated_at >= :from_ts and t.activated_at < :to_ts "
        "     and ((t.direction = 'Long' and t.current_stop_price < t.stop_price) "
        "       or (t.direction = 'Short' and t.current_stop_price > t.stop_price))) "
        "    as stop_widened_trades, "
        "  (select count(*) from daily_reflections d where d.user_id = bt.user_id "
        "     and d.saved_at >= :from_ts and d.saved_at < :to_ts) as daily_reflections "
        "from beta_testers bt "
        "where bt.is_active = true "
        "  and (cast(:phase as text) is null "
        "    or bt.beta_phase::text = cast(:phase as text)) "
        "order by days_active desc nulls last, bt.email"
    )
    rows = (await session.execute(sql, params)).mappings().all()
    return [dict(r) for r in rows]
