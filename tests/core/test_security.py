"""Offline tests for JWKS/ES256 verification.

No network: an EC P-256 keypair is generated in-test, tokens are signed with the
private key, and the JWKS client is monkeypatched to return the matching public
key. Covers the valid path plus every rejection path.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from standfast.core import security

SUB = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def signing_keys(monkeypatch: pytest.MonkeyPatch) -> ec.EllipticCurvePrivateKey:
    """Generate a keypair, point the verifier's JWKS client at the public key,
    and return the private key for signing test tokens."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    fake_key = SimpleNamespace(key=private_key.public_key())
    fake_client = SimpleNamespace(get_signing_key_from_jwt=lambda _token: fake_key)
    monkeypatch.setattr(security, "_jwk_client", lambda: fake_client)
    return private_key


def _base_claims(**overrides: object) -> dict[str, object]:
    now = dt.datetime.now(dt.UTC)
    claims: dict[str, object] = {
        "sub": SUB,
        "email": "founder@standfastech.com",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": now + dt.timedelta(hours=1),
    }
    claims.update(overrides)
    return claims


def _sign(key: object, claims: dict[str, object], alg: str = "ES256") -> str:
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": "test"})


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_valid_token_returns_current_user(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    token = _sign(signing_keys, _base_claims())
    user = await security.get_current_user(_creds(token))
    assert user.id == SUB
    assert user.email == "founder@standfastech.com"
    assert user.role == "authenticated"


async def test_expired_token_rejected(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    expired = _base_claims(exp=dt.datetime.now(dt.UTC) - dt.timedelta(hours=1))
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(_creds(_sign(signing_keys, expired)))
    assert exc.value.status_code == 401


async def test_missing_sub_rejected(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    claims = _base_claims()
    del claims["sub"]
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(_creds(_sign(signing_keys, claims)))
    assert exc.value.status_code == 401


async def test_wrong_audience_rejected(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    token = _sign(signing_keys, _base_claims(aud="some-other-aud"))
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(_creds(token))
    assert exc.value.status_code == 401


async def test_hs256_token_rejected(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    # A token signed with HS256 must be refused — algorithm not in the allow-list.
    secret = "x" * 32  # >=32 bytes to avoid PyJWT's short-key warning
    token = _sign(secret, _base_claims(), alg="HS256")
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(_creds(token))
    assert exc.value.status_code == 401


async def test_wrong_signature_rejected(
    signing_keys: ec.EllipticCurvePrivateKey,
) -> None:
    # Signed by a DIFFERENT key than the JWKS client returns.
    other_key = ec.generate_private_key(ec.SECP256R1())
    token = _sign(other_key, _base_claims())
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(_creds(token))
    assert exc.value.status_code == 401


async def test_missing_bearer_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        await security.get_current_user(None)
    assert exc.value.status_code == 401
