"""Register a domain in Resend and print the DNS records to publish.

Usage:
    uv run python scripts/register_resend_domain.py            # uses standfastech.com
    uv run python scripts/register_resend_domain.py example.io

Reads `RESEND_API_KEY` from `.env` via core.config. The key never appears in
this file or on stdout. Idempotent: re-running on an already-registered domain
fetches and re-prints the records and current status.

After publishing the records at your DNS provider, Resend auto-verifies once
DNS propagates (usually minutes to a couple hours).
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx

from standfast.core.config import get_settings

DEFAULT_DOMAIN = "standfastech.com"
API = "https://api.resend.com"


async def get_or_create_domain(
    client: httpx.AsyncClient, key: str, name: str
) -> dict[str, Any]:
    auth = {"Authorization": f"Bearer {key}"}

    created = await client.post(f"{API}/domains", json={"name": name}, headers=auth)
    if created.status_code < 400:
        return created.json()

    if created.status_code in (403, 422) and "already" in created.text.lower():
        listing = await client.get(f"{API}/domains", headers=auth)
        listing.raise_for_status()
        for d in listing.json().get("data", []):
            if d["name"].lower() == name.lower():
                detail = await client.get(f"{API}/domains/{d['id']}", headers=auth)
                detail.raise_for_status()
                return detail.json()
        raise RuntimeError(f"Resend reports {name} exists but it's not in /domains")

    created.raise_for_status()
    return {}  # unreachable — raise_for_status above will throw


def print_records(domain: dict[str, Any]) -> None:
    print()
    print(f"=== Resend domain: {domain['name']} ===")
    print(f"Status:    {domain.get('status', 'unknown')}")
    print(f"Domain ID: {domain['id']}")
    print(f"Region:    {domain.get('region', '?')}")
    print()
    print(f"Publish these records at your DNS provider for {domain['name']}:")
    print()
    for i, r in enumerate(domain.get("records", []), start=1):
        host = r.get("name", "")
        rtype = r.get("type", "")
        value = r.get("value", "")
        priority = r.get("priority")
        ttl = r.get("ttl", "Auto")
        print(f"  [{i}] {r.get('record', '')}")
        print(f"      Type:     {rtype}")
        print(f"      Host:     {host}")
        if priority is not None:
            print(f"      Priority: {priority}")
        print(f"      TTL:      {ttl}")
        print(f"      Value:    {value}")
        print()
    if domain.get("status") == "not_started":
        print("Note: once records are published, Resend will verify automatically.")
        print("Re-run this script to see updated status.")


async def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DOMAIN
    settings = get_settings()
    if not settings.resend_api_key:
        print("ERROR: RESEND_API_KEY is not set in standfast-backend/.env", file=sys.stderr)
        return 1

    async with httpx.AsyncClient(timeout=20.0) as client:
        domain = await get_or_create_domain(client, settings.resend_api_key, name)

    print_records(domain)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
