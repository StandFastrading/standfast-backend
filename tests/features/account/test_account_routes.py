"""Auth-gated route smoke test.

Verifies the JWT dependency rejects requests with no Authorization header. Full
end-to-end tests (mint a JWT, hit /me, assert the profile is persisted) need a
test Postgres fixture — add when we wire CI.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_me_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/account/me")
    assert response.status_code == 401
