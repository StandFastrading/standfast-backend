"""Broadcasts business logic.

Callable from routers OR background tasks — no FastAPI imports.

The flow for `send_broadcast`:
  1. Load all Supabase auth users.
  2. Drop anyone already in `email_unsubscribes` and anyone without an email.
  3. For each remaining user, generate a per-recipient HMAC unsubscribe token,
     append a footer with the unsubscribe link, send via Resend.
  4. Failures are swallowed per-recipient and counted — one bad address must
     not abort the whole broadcast.

Tokens are stateless: token = `user_id.b64u_sig`. No table of pending tokens.
Anyone who can forge a SHA-256 HMAC under `UNSUBSCRIBE_SECRET` is the only
person who can craft a working link.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from urllib.parse import quote
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from standfast.core.config import get_settings
from standfast.core.errors import AppError
from standfast.integrations import resend, supabase

from . import repository
from .schemas import BroadcastRequest, BroadcastResult

log = logging.getLogger(__name__)


class BroadcastConfigError(AppError):
    """Resend / unsubscribe env vars are missing."""

    status_code = 503
    code = "broadcast_not_configured"


def _require_unsubscribe_secret() -> bytes:
    settings = get_settings()
    if not settings.unsubscribe_secret:
        raise BroadcastConfigError("UNSUBSCRIBE_SECRET is not set")
    return settings.unsubscribe_secret.encode("utf-8")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_unsubscribe_token(user_id: UUID) -> str:
    secret = _require_unsubscribe_secret()
    sig = hmac.new(secret, str(user_id).encode("utf-8"), hashlib.sha256).digest()
    return f"{user_id}.{_b64u(sig)}"


def verify_unsubscribe_token(token: str) -> UUID:
    """Returns the user_id if the token is valid; raises ValueError otherwise."""
    secret = _require_unsubscribe_secret()
    try:
        user_part, sig_part = token.split(".", 1)
        provided_sig = _b64u_decode(sig_part)
    except (ValueError, base64.binascii.Error) as e:  # type: ignore[attr-defined]
        raise ValueError("malformed token") from e

    expected_sig = hmac.new(secret, user_part.encode("utf-8"), hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ValueError("bad signature")

    try:
        return UUID(user_part)
    except ValueError as e:
        raise ValueError("malformed user_id") from e


def _build_unsubscribe_url(user_id: UUID) -> str:
    settings = get_settings()
    token = sign_unsubscribe_token(user_id)
    return f"{settings.public_api_base_url.rstrip('/')}/api/v1/unsubscribe/{quote(token)}"


def _append_footer(html: str, unsubscribe_url: str) -> str:
    footer = (
        '<hr style="margin-top:32px;border:none;border-top:1px solid #e5e7eb"/>'
        '<p style="color:#6b7280;font-size:12px;margin-top:16px">'
        "You're receiving this because you have a Standfast account. "
        f'<a href="{unsubscribe_url}">Unsubscribe</a>.'
        "</p>"
    )
    return html + footer


async def send_broadcast(session: AsyncSession, payload: BroadcastRequest) -> BroadcastResult:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise BroadcastConfigError("RESEND_API_KEY and RESEND_FROM_EMAIL must be set")
    _require_unsubscribe_secret()  # fail fast if signing key is missing

    unsubscribed = await repository.list_unsubscribed_user_ids(session)
    users = await supabase.list_auth_users()

    sent = failed = skipped_unsub = skipped_no_email = 0

    for user in users:
        try:
            user_uuid = UUID(user.id)
        except ValueError:
            log.warning("supabase user has non-uuid id, skipping: %s", user.id)
            failed += 1
            continue

        if user_uuid in unsubscribed:
            skipped_unsub += 1
            continue
        if not user.email:
            skipped_no_email += 1
            continue

        unsubscribe_url = _build_unsubscribe_url(user_uuid)
        html = _append_footer(payload.html, unsubscribe_url)
        headers = {"List-Unsubscribe": f"<{unsubscribe_url}>"}

        try:
            await resend.send_email(
                to=user.email,
                subject=payload.subject,
                html=html,
                text=payload.text,
                headers=headers,
            )
            sent += 1
        except resend.ResendError as e:
            log.warning("resend send failed for %s: %s", user.email, e.message)
            failed += 1

    return BroadcastResult(
        sent=sent,
        failed=failed,
        unsubscribed_skipped=skipped_unsub,
        no_email_skipped=skipped_no_email,
    )


async def record_unsubscribe(session: AsyncSession, token: str) -> UUID:
    """Verify the token and persist the opt-out. Returns the user_id."""
    try:
        user_id = verify_unsubscribe_token(token)
    except ValueError as e:
        raise AppError("invalid unsubscribe token", code="invalid_token") from e

    user = await supabase.get_auth_user(str(user_id))
    email = (user.email if user else None) or ""
    await repository.upsert_unsubscribe(session, user_id=user_id, email=email)
    return user_id
