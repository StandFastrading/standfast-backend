"""Test setup. Sets safe env vars BEFORE the app imports so `get_settings()`
caches dummy values instead of complaining about a missing .env."""

from __future__ import annotations

import os

# Must happen before any `standfast.*` import below.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/standfast_test"
)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient

from standfast.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
