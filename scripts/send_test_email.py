"""One-shot Resend smoke test.

Sends a test email to a hard-coded list to confirm RESEND_API_KEY + domain
verification work end-to-end. Uses the same `integrations/resend.py` client
the backend uses — so a successful send here proves the production code path.

Usage:
    uv run python scripts/send_test_email.py
"""

from __future__ import annotations

import asyncio

from standfast.integrations import resend

RECIPIENTS = [
    "cruz@atomiktrading.io",
    "turnereric33@yahoo.com",
]

SUBJECT = "Standfast — Resend integration test"
HTML = """\
<div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;color:#111">
  <h1 style="font-size:22px">Standfast email is live</h1>
  <p>This is a test send to confirm the Resend integration is wired up correctly.</p>
  <p>If you're seeing this, the backend can now send project updates from
     <code>founder@standfastech.com</code> via Resend.</p>
  <p style="color:#6b7280;font-size:13px;margin-top:24px">
    — Sent automatically from the Standfast backend smoke test.
  </p>
</div>
"""
TEXT = (
    "Standfast email is live.\n\n"
    "This is a test send to confirm the Resend integration is wired up correctly.\n"
    "If you're seeing this, the backend can now send project updates from "
    "founder@standfastech.com via Resend.\n"
)


async def main() -> None:
    for to in RECIPIENTS:
        try:
            message_id = await resend.send_email(
                to=to,
                subject=SUBJECT,
                html=HTML,
                text=TEXT,
            )
            print(f"  OK   {to}  (resend id: {message_id})")
        except resend.ResendError as e:
            print(f"  FAIL {to}  ({e.status_code or '?'}: {e.message})")


if __name__ == "__main__":
    asyncio.run(main())
