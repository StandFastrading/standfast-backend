"""Tests for the broadcasts feature.

These cover pure logic (HMAC token roundtrip) and route gating (admin auth,
unauthenticated requests). Full DB integration is deferred to CI once a
test Postgres fixture exists — see tests/conftest.py.
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient


def _set_broadcast_env() -> None:
    os.environ.setdefault("RESEND_API_KEY", "test-resend-key")
    os.environ.setdefault("RESEND_FROM_EMAIL", "founder@standfastech.com")
    os.environ.setdefault("UNSUBSCRIBE_SECRET", "test-unsubscribe-secret-32-bytes-min")
    os.environ.setdefault("ADMIN_EMAILS", "admin@standfastech.com")
    os.environ.setdefault("PUBLIC_API_BASE_URL", "http://testserver")
    # Clear cached settings so the new env vars are picked up.
    from standfast.core.config import get_settings

    get_settings.cache_clear()


_set_broadcast_env()


def test_post_broadcast_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/broadcasts", json={"subject": "hi", "html": "<p>hi</p>"}
    )
    assert response.status_code == 401


def test_unsubscribe_with_garbage_token_returns_400(client: TestClient) -> None:
    response = client.get("/api/v1/unsubscribe/not-a-valid-token")
    assert response.status_code == 400
    assert "invalid" in response.text.lower()


def test_signed_token_roundtrip() -> None:
    from standfast.features.broadcasts.service import (
        sign_unsubscribe_token,
        verify_unsubscribe_token,
    )

    user_id = uuid4()
    token = sign_unsubscribe_token(user_id)
    assert verify_unsubscribe_token(token) == user_id


def test_tampered_token_rejected() -> None:
    from standfast.features.broadcasts.service import (
        sign_unsubscribe_token,
        verify_unsubscribe_token,
    )

    token = sign_unsubscribe_token(uuid4())
    # Swap the user_id part for a different uuid but keep the original signature.
    _, sig = token.split(".", 1)
    tampered = f"{uuid4()}.{sig}"
    with pytest.raises(ValueError):
        verify_unsubscribe_token(tampered)


def test_malformed_token_rejected() -> None:
    from standfast.features.broadcasts.service import verify_unsubscribe_token

    with pytest.raises(ValueError):
        verify_unsubscribe_token("no-dot-separator")


def test_unsubscribe_token_uuid_in_payload() -> None:
    """The token must contain the user_id as plaintext so verification is stateless."""
    from standfast.features.broadcasts.service import sign_unsubscribe_token

    user_id = UUID("12345678-1234-5678-1234-567812345678")
    token = sign_unsubscribe_token(user_id)
    assert token.startswith(str(user_id) + ".")
