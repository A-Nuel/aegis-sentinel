"""Orbio credit loop stub.

Wire these to Orbio MCP tools once the wallet is approved:
  orbio_get_balance, orbio_claim_key, orbio_get_key_status,
  orbio_top_up_key, orbio_rotate_key, orbio_delete_key
"""

from __future__ import annotations

from typing import Any

from app.config import settings


class CreditLoop:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        return {
            "key_configured": bool(settings.openrouter_api_key),
            "low_threshold_usd": settings.credit_low_threshold_usd,
            "events": self.events[-20:],
            "note": "MCP live calls land here after Orbio approval",
        }

    def record(self, action: str, detail: str) -> None:
        self.events.append({"action": action, "detail": detail})


credit_loop = CreditLoop()
