"""The beta-admin endpoints must reject unauthenticated callers (admin-gated)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_testers_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/beta/admin/testers").status_code == 401


def test_create_tester_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/beta/admin/testers",
        json={"email": "x@example.com", "beta_phase": "phase_1"},
    )
    assert resp.status_code == 401


def test_update_tester_requires_auth(client: TestClient) -> None:
    resp = client.patch(
        "/api/v1/beta/admin/testers/00000000-0000-0000-0000-000000000000",
        json={"is_active": False},
    )
    assert resp.status_code == 401
