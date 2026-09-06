"""Self-funding credit loop for Orbio.

Runtime: tracks key presence + best-effort status against the gateway.
MCP (after wallet auth): orbio_get_balance, orbio_claim_key, orbio_get_key_status,
orbio_top_up_key, orbio_rotate_key, orbio_delete_key @ https://www.orbio.so/api/mcp
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
            "key_configured": bool(settings.llm_api_key),
            "base_url": settings.llm_base_url,
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

    def gateway_key_info(self) -> dict[str, Any]:
        if not settings.llm_api_key:
            return {"ok": False, "reason": "missing ORBIO_API_KEY"}
        # OpenRouter-compatible /key when the gateway exposes it
        try:
            with httpx.Client(timeout=20) as client:
                r = client.get(
                    f"{settings.llm_base_url}/key",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    self.record("key_status", "gateway /key ok")
                    return {"ok": True, "provider": "orbio", "data": data}
                self.record("key_status", f"status {r.status_code}")
                return {"ok": False, "reason": f"http {r.status_code}", "body": r.text[:300]}
        except Exception as exc:
            self.record("key_status_error", str(exc))
            return {"ok": False, "reason": str(exc)}

    def openrouter_key_info(self) -> dict[str, Any]:
        return self.gateway_key_info()

    def remaining_usd_estimate(self, key_info: dict[str, Any]) -> float | None:
        if not key_info.get("ok"):
            return None
        data = key_info.get("data") or {}
        blob = data.get("data") if isinstance(data.get("data"), dict) else data
        if isinstance(blob, dict):
            limit = blob.get("limit")
            usage = blob.get("usage")
            if limit is not None and usage is not None:
                try:
                    return float(limit) - float(usage)
                except (TypeError, ValueError):
                    pass
            for key in ("limit_remaining", "remaining"):
                if key in blob and isinstance(blob[key], (int, float)):
                    return float(blob[key])
        return None

    def ensure_funded(self) -> dict[str, Any]:
        if not settings.llm_api_key:
            self.record("skip", "no ORBIO_API_KEY")
            self.last_status = {"ok": False, "reason": "missing key"}
            return self.last_status

        info = self.gateway_key_info()
        remaining = self.remaining_usd_estimate(info)
        result: dict[str, Any] = {
            "ok": True,
            "key_present": True,
            "base_url": settings.llm_base_url,
            "gateway": info,
            "remaining_usd": remaining,
            "action": "none",
        }
        if remaining is not None and remaining < settings.credit_low_threshold_usd:
            self.record(
                "top_up_needed",
                f"remaining ${remaining:.4f} < threshold ${settings.credit_low_threshold_usd}",
            )
            result["action"] = "top_up_needed"
            result["mcp_hint"] = "Use Orbio MCP: orbio_get_balance then orbio_top_up_key"
        else:
            self.record(
                "healthy",
                f"remaining={remaining}" if remaining is not None else "key live",
            )
            result["action"] = "healthy"
        self.last_status = result
        return result


credit_loop = CreditLoop()
