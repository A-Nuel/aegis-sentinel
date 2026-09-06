"""Self-funding credit loop for Orbio Build Week.

Runtime path (works today):
  - Tracks OPENROUTER_API_KEY presence
  - Polls OpenRouter key/usage when possible
  - Logs every decision so judges can see self-management

MCP path (after wallet auth in Claude Code / agent host):
  orbio_get_balance, orbio_claim_key, orbio_get_key_status,
  orbio_top_up_key, orbio_rotate_key, orbio_delete_key
  Endpoint: https://www.orbio.so/api/mcp
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class CreditLoop:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.last_status: dict[str, Any] = {}

    def record(self, action: str, detail: str = "", **extra: Any) -> None:
        row = {"ts": time.time(), "action": action, "detail": detail, **extra}
        self.events.append(row)
        if len(self.events) > 200:
            self.events = self.events[-200:]

    def status(self) -> dict[str, Any]:
        return {
            "key_configured": bool(settings.openrouter_api_key),
            "low_threshold_usd": settings.credit_low_threshold_usd,
            "last_status": self.last_status,
            "events": self.events[-30:],
            "mcp_endpoint": "https://www.orbio.so/api/mcp",
            "mcp_tools": [
                "orbio_get_balance",
                "orbio_claim_key",
                "orbio_get_key_status",
                "orbio_top_up_key",
                "orbio_rotate_key",
                "orbio_delete_key",
            ],
        }

    def openrouter_key_info(self) -> dict[str, Any]:
        """Best-effort live usage from OpenRouter (Orbio-issued keys work here)."""
        if not settings.openrouter_api_key:
            return {"ok": False, "reason": "missing OPENROUTER_API_KEY"}
        try:
            with httpx.Client(timeout=20) as client:
                # Key metadata / limits when exposed by OpenRouter
                r = client.get(
                    "https://openrouter.ai/api/v1/key",
                    headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    self.record("key_status", "openrouter /key ok", raw=str(data)[:500])
                    return {"ok": True, "provider": "openrouter", "data": data}
                self.record("key_status", f"openrouter status {r.status_code}")
                return {
                    "ok": False,
                    "reason": f"http {r.status_code}",
                    "body": r.text[:300],
                }
        except Exception as exc:
            self.record("key_status_error", str(exc))
            return {"ok": False, "reason": str(exc)}

    def remaining_usd_estimate(self, key_info: dict[str, Any]) -> float | None:
        if not key_info.get("ok"):
            return None
        data = key_info.get("data") or {}
        # OpenRouter shapes vary; try common fields
        for path in (
            ("data", "limit_remaining"),
            ("data", "usage"),
            ("limit_remaining",),
            ("usage",),
        ):
            cur: Any = data
            ok = True
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, (int, float)):
                return float(cur)
        limit = None
        usage = None
        blob = data.get("data") if isinstance(data.get("data"), dict) else data
        if isinstance(blob, dict):
            limit = blob.get("limit")
            usage = blob.get("usage")
            if limit is not None and usage is not None:
                try:
                    return float(limit) - float(usage)
                except (TypeError, ValueError):
                    pass
        return None

    def ensure_funded(self) -> dict[str, Any]:
        """Core self-sustaining step called every runner cycle."""
        if not settings.openrouter_api_key:
            self.record("skip", "no OPENROUTER_API_KEY — claim via Orbio dashboard/MCP")
            self.last_status = {"ok": False, "reason": "missing key"}
            return self.last_status

        info = self.openrouter_key_info()
        remaining = self.remaining_usd_estimate(info)

        result: dict[str, Any] = {
            "ok": True,
            "key_present": True,
            "openrouter": info,
            "remaining_usd": remaining,
            "action": "none",
        }

        if remaining is not None and remaining < settings.credit_low_threshold_usd:
            # MCP top-up is authenticated browser-side; we log the intent loudly
            self.record(
                "top_up_needed",
                f"remaining ${remaining:.4f} < threshold ${settings.credit_low_threshold_usd}",
            )
            result["action"] = "top_up_needed"
            result["mcp_hint"] = (
                "Call orbio_get_balance then orbio_top_up_key (or orbio_claim_key) "
                "via https://www.orbio.so/api/mcp after wallet auth"
            )
        else:
            self.record(
                "healthy",
                f"remaining={remaining}" if remaining is not None else "key live, limit unknown",
            )
            result["action"] = "healthy"

        self.last_status = result
        return result


credit_loop = CreditLoop()
