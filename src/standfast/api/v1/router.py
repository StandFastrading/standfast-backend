"""Aggregate all v1 sub-routers. New feature routers go here."""

from __future__ import annotations

from fastapi import APIRouter

from . import account, analytics, desk, journal, onboarding, rules_risk, trades

api_v1_router = APIRouter()
api_v1_router.include_router(account.router, prefix="/account", tags=["account"])
api_v1_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_v1_router.include_router(rules_risk.router, prefix="/rules-risk", tags=["rules-risk"])
api_v1_router.include_router(desk.router, prefix="/desk", tags=["desk"])
api_v1_router.include_router(journal.router, prefix="/journal", tags=["journal"])
api_v1_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_v1_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
