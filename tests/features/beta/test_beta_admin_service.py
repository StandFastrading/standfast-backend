"""Unit tests for admin tester management — fakes the repository, no DB."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from standfast.core.errors import ConflictError, NotFoundError
from standfast.features.beta import repository, service
from standfast.features.beta.schemas import BetaTesterCreate, BetaTesterUpdate


class _FakeSession:
    async def flush(self) -> None:
        return None


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _async_return(value: object):  # type: ignore[no-untyped-def]
    async def _inner(*_args: object, **_kwargs: object) -> object:
        return value

    return _inner


def _tester(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid4(),
        "email": "t@example.com",
        "beta_phase": "phase_1",
        "is_active": True,
        "user_id": None,
        "last_seen_at": None,
        "created_at": datetime.now(UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_create_tester_rejects_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(_tester()))
    with pytest.raises(ConflictError):
        _run(
            service.create_tester(
                _FakeSession(),
                BetaTesterCreate(email="t@example.com", beta_phase="phase_1"),
            )
        )


def test_create_tester_inserts_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "find_tester_by_email", _async_return(None))

    async def fake_insert(_session: object, tester: object) -> object:
        return tester

    monkeypatch.setattr(repository, "insert_tester", fake_insert)

    result = _run(
        service.create_tester(
            _FakeSession(),
            BetaTesterCreate(email="  NEW@Example.COM ", beta_phase="phase_2"),
        )
    )
    assert result.email == "new@example.com"  # normalized by the schema
    assert result.beta_phase == "phase_2"
    assert result.is_active is True
    assert result.user_id is None


def test_update_tester_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repository, "get_tester_by_id", _async_return(None))
    with pytest.raises(NotFoundError):
        _run(
            service.update_tester(
                _FakeSession(), uuid4(), BetaTesterUpdate(is_active=False)
            )
        )


def test_update_tester_sets_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    tester = _tester(is_active=True, beta_phase="phase_1")
    monkeypatch.setattr(repository, "get_tester_by_id", _async_return(tester))

    result = _run(
        service.update_tester(
            _FakeSession(),
            tester.id,
            BetaTesterUpdate(is_active=False, beta_phase="phase_2"),
        )
    )
    assert tester.is_active is False
    assert tester.beta_phase == "phase_2"
    assert result.is_active is False
    assert result.beta_phase == "phase_2"
