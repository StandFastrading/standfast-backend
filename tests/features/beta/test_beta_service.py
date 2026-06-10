"""Unit tests for beta entry gate logic + the happy-path session mint.

These avoid Postgres by faking the repository, the Supabase admin calls, and the
session — the goal is to pin the validation rules and the user_id persistence
that keeps a tester's data connected across visits.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from standfast.core.errors import ForbiddenError
from standfast.features.beta import repository, service
from standfast.integrations import supabase


class _FakeSession:
    async def flush(self) -> None:
        return None


def _tester(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid4(),
        "email": "tester@example.com",
        "beta_phase": "phase_1",
        "is_active": True,
        "user_id": None,
        "last_seen_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def test_rejects_unknown_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(None))

    with pytest.raises(ForbiddenError) as exc:
        _run(service.enter_beta(_FakeSession(), email="nope@example.com", access_code="betaphase1"))
    assert exc.value.code == "not_approved"


def test_rejects_inactive_tester(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repository, "find_tester_by_email", _async_return(_tester(is_active=False))
    )

    with pytest.raises(ForbiddenError) as exc:
        _run(
            service.enter_beta(
                _FakeSession(), email="tester@example.com", access_code="betaphase1"
            )
        )
    assert exc.value.code == "tester_inactive"


def test_rejects_code_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(_tester()))
    monkeypatch.setattr(repository, "get_active_code_for_phase", _async_return("betaphase1"))

    with pytest.raises(ForbiddenError) as exc:
        _run(service.enter_beta(_FakeSession(), email="tester@example.com", access_code="wrong"))
    assert exc.value.code == "bad_access_code"


def test_first_entry_creates_user_and_mints_session(monkeypatch: pytest.MonkeyPatch) -> None:
    tester = _tester(user_id=None)
    new_user_id = str(uuid4())

    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(tester))
    monkeypatch.setattr(repository, "get_active_code_for_phase", _async_return("betaphase1"))
    monkeypatch.setattr(supabase, "create_auth_user", _async_return(None))
    monkeypatch.setattr(
        supabase,
        "mint_session",
        _async_return(
            supabase.SessionTokens(
                access_token="acc",
                refresh_token="ref",
                expires_in=3600,
                user_id=new_user_id,
            )
        ),
    )

    result = _run(
        service.enter_beta(_FakeSession(), email="tester@example.com", access_code="betaphase1")
    )

    assert result.is_new is True
    assert result.beta_phase == "phase_1"
    assert result.access_token == "acc"
    assert result.refresh_token == "ref"
    # The tester is now bound to the minted auth user for all future visits.
    assert str(tester.user_id) == new_user_id
    assert tester.last_seen_at is not None


def test_returning_entry_is_not_new(monkeypatch: pytest.MonkeyPatch) -> None:
    existing_id = uuid4()
    tester = _tester(user_id=existing_id)

    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(tester))
    monkeypatch.setattr(repository, "get_active_code_for_phase", _async_return("betaphase1"))
    monkeypatch.setattr(
        supabase,
        "mint_session",
        _async_return(
            supabase.SessionTokens(
                access_token="acc",
                refresh_token="ref",
                expires_in=3600,
                user_id=str(existing_id),
            )
        ),
    )

    result = _run(
        service.enter_beta(_FakeSession(), email="tester@example.com", access_code="betaphase1")
    )

    assert result.is_new is False
    assert str(tester.user_id) == str(existing_id)


def _async_return(value: object):  # type: ignore[no-untyped-def]
    async def _inner(*_args: object, **_kwargs: object) -> object:
        return value

    return _inner
