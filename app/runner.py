"""Continuous multi-chain scan loop."""

from __future__ import annotations

import time

from app.config import settings
from app.engine.credits import credit_loop
from app.engine.sentinel import sentinel


def main() -> None:
    print("Aegis Sentinel runner started")
    print(f"Chains: {settings.chains_list}")
    print(f"Interval: {settings.scan_interval_seconds}s")
    while True:
        credit_loop.ensure_funded()
        for chain in settings.chains_list:
            try:
                result = sentinel.scan_latest_block(chain, enrich=bool(settings.openrouter_api_key))
                print(f"[{chain}] new_alerts={result['new_alerts']}")
                for a in result.get("alerts") or []:
                    print(f"  - {a.get('severity')} {a.get('type')}: {a.get('details')}")
            except Exception as exc:
                print(f"[{chain}] error: {exc}")
        time.sleep(settings.scan_interval_seconds)


if __name__ == "__main__":
    main()
