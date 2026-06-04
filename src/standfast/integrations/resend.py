"""Resend HTTP client. One outbound function: send_email().

Resend's REST API: https://resend.com/docs/api-reference/emails/send-email
Auth is Bearer-token over HTTPS. Requires `RESEND_API_KEY` + `RESEND_FROM_EMAIL`
in env (see core/config.py). Errors raise ResendError with the API's message.
"""

from __future__ import annotations

from typing import Any

import httpx

from standfast.core.config import get_settings

_RESEND_API = "https://api.resend.com/emails"


class ResendError(Exception):
    """Raised when Resend responds non-2xx or the SDK is misconfigured."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
    headers: dict[str, str] | None = None,
    reply_to: str | None = None,
) -> str:
    """Send one email. Returns Resend's message id on success."""
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise ResendError("RESEND_API_KEY and RESEND_FROM_EMAIL must be set")

    payload: dict[str, Any] = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text is not None:
        payload["text"] = text
    if headers:
        payload["headers"] = headers
    if reply_to:
        payload["reply_to"] = reply_to

    async with httpx.AsyncClient(timeout=15.0) as http:
        response = await http.post(
            _RESEND_API,
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        )

    if response.status_code >= 400:
        try:
            detail = response.json().get("message", response.text)
        except ValueError:
            detail = response.text
        raise ResendError(
            f"resend {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    return str(response.json().get("id", ""))
