"""Continuous multi-chain agent loop: credits → scan → log."""

from __future__ import annotations

import time

from app.config import settings
from app.engine.credits import credit_loop
from app.engine.sentinel import sentinel


def main() -> None:
    print("=== Aegis Sentinel agent loop ===")
    print(f"Chains: {settings.chains_list}")
    print(f"Interval: {settings.scan_interval_seconds}s")
    print(f"LLM base: {settings.llm_base_url}")
    print(f"Orbio key set: {bool(settings.llm_api_key)}")
    cycle = 0
    while True:
        cycle += 1
        print(f"\n--- cycle {cycle} ---")
        funded = credit_loop.ensure_funded()
        print(f"credits: action={funded.get('action')} remaining={funded.get('remaining_usd')}")

        enrich = bool(settings.llm_api_key)
        for chain in settings.chains_list:
            try:
                result = sentinel.scan_latest_block(chain, enrich=enrich)
                print(f"[{chain}] new_alerts={result['new_alerts']}")
                for a in result.get("alerts") or []:
                    print(
                        f"  - {a.get('severity')} {a.get('type')}: "
                        f"{a.get('llm_summary') or a.get('details')}"
                    )
            except Exception as exc:
                print(f"[{chain}] error: {exc}")

        time.sleep(settings.scan_interval_seconds)


if __name__ == "__main__":
    main()
