"""LLM via Orbio OpenAI-compatible gateway (or OpenRouter-compatible fallback)."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import settings


class LLM:
    def score_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        if not settings.llm_api_key:
            return {
                "severity": alert.get("severity", "Medium"),
                "summary": alert.get("details", ""),
                "source": "heuristic",
            }

        prompt = (
            "You are a DeFi security analyst. Score this on-chain event.\n"
            "Return ONLY JSON: {\"severity\": \"Critical|High|Medium|Low\", \"summary\": \"...\"}\n\n"
            f"Event: {json.dumps(alert, default=str)}"
        )
        try:
            with httpx.Client(timeout=45) as client:
                r = client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/A-Nuel/aegis-sentinel",
                        "X-Title": "Aegis Sentinel",
                    },
                    json={
                        "model": settings.orbio_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                    },
                )
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
                match = re.search(r"\{[\s\S]*\}", text)
                if match:
                    data = json.loads(match.group(0))
                    data["source"] = "orbio"
                    return data
        except Exception as exc:
            return {
                "severity": alert.get("severity", "Medium"),
                "summary": f"LLM fallback: {alert.get('details')} ({exc})",
                "source": "fallback",
            }
        return {
            "severity": alert.get("severity", "Medium"),
            "summary": alert.get("details", ""),
            "source": "heuristic",
        }


llm = LLM()
