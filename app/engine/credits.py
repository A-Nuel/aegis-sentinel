"""Orbio credit self-management stub.

After approval, map these to MCP tools:
  orbio_get_balance, orbio_claim_key, orbio_get_key_status,
  orbio_top_up_key, orbio_rotate_key, orbio_delete_key
"""

from __future__ import annotations

import time
from typing import Any

from app.config import settings


class CreditLoop:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def status(self) -> dict[str, Any]:
        return {
            "key_configured": bool(settings.openrouter_api_key),
            "low_threshold_usd": settings.credit_low_threshold_usd,
            "events": self.events[-30:],
            "mcp": "pending — wire after Orbio key claim",
        }

    def record(self, action: str, detail: str = "") -> None:
        self.events.append({"ts": time.time(), "action": action, "detail": detail})

    def ensure_funded(self) -> dict[str, Any]:
        """Placeholder for MCP top-up."""
        if not settings.openrouter_api_key:
            self.record("skip", "no OPENROUTER_API_KEY")
            return {"ok": False, "reason": "missing key"}
        self.record("check", "key present — MCP not yet connected")
        return {"ok": True, "reason": "key present"}


credit_loop = CreditLoop()
