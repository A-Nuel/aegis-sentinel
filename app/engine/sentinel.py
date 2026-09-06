"""Live-block threat sentinel for continuous DeFi monitoring."""

from __future__ import annotations

import time
from typing import Any

from web3 import Web3

from app.core.llm import llm
from app.core.rpc import rpc
from app.core.storage import store

# Function selectors / markers commonly seen in risky flows
FLASH_SIGS = (
    "ab963c34",  # flashLoan
    "5cffe9de",  # flashLoanSimple-ish patterns
    "flashloan",
    "a0712d68",
)
ADMIN_HINTS = (
    "845dd321",  # pause variants appear as text too
    "f2fde38b",  # transferOwnership
    "pause(",
    "unpause(",
    "transferownership",
    "renounceownership",
    "updateowner",
)
ORACLE_HINTS = ("setprice", "updateprice", "latestanswer", "submitvalue")


class Sentinel:
    def watch(self, address: str, chain: str = "ethereum", label: str = "") -> dict[str, str]:
        addr = Web3.to_checksum_address(address)
        return store.add_watch(addr, chain.lower(), label or addr[:10])

    def unwatch(self, address: str, chain: str = "ethereum") -> bool:
        return store.remove_watch(Web3.to_checksum_address(address), chain.lower())

    @property
    def watched(self) -> list[dict[str, str]]:
        return store.list_watched()

    def scan_latest_block(self, chain: str = "ethereum", enrich: bool = True) -> dict[str, Any]:
        chain = chain.lower()
        new_alerts: list[dict[str, Any]] = []
        try:
            w3 = rpc.get_web3(chain)
            block = w3.eth.get_block("latest", full_transactions=True)
            block_num = int(block["number"])
            for tx in list(block.get("transactions") or [])[:40]:
                alert = self._inspect_tx(w3, chain, block_num, tx)
                if not alert:
                    continue
                if store.alert_exists(alert["id"]):
                    continue
                if enrich:
                    scored = llm.score_alert(alert)
                    alert["severity"] = scored.get("severity", alert["severity"])
                    alert["llm_summary"] = scored.get("summary", "")
                    alert["llm_source"] = scored.get("source", "")
                store.save_alert(alert)
                new_alerts.append(alert)
        except Exception as exc:
            err = {
                "id": f"ERR-{chain}-{int(time.time())}",
                "timestamp": time.time(),
                "chain": chain,
                "type": "SCAN_ERROR",
                "severity": "Low",
                "details": str(exc),
            }
            if not store.alert_exists(err["id"]):
                store.save_alert(err)
                new_alerts.append(err)
        return {"chain": chain, "new_alerts": len(new_alerts), "alerts": new_alerts}

    def _inspect_tx(self, w3: Web3, chain: str, block_num: int, tx: Any) -> dict[str, Any] | None:
        raw_input = str(tx.get("input") or "").lower()
        tx_hash = tx.get("hash")
        tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        value_eth = float(w3.from_wei(tx.get("value") or 0, "ether"))

        kind = severity = details = None
        if any(sig in raw_input for sig in FLASH_SIGS):
            kind, severity, details = "FLASH_LOAN", "High", "Flash-loan related calldata detected"
        elif value_eth >= 500:
            kind, severity, details = (
                "WHALE_TRANSFER",
                "Medium",
                f"{value_eth:,.2f} native units transferred",
            )
        elif any(h in raw_input for h in ADMIN_HINTS):
            kind, severity, details = (
                "ADMIN_STATE_CHANGE",
                "High",
                "pause / ownership / admin-style call pattern",
            )
        elif any(h in raw_input for h in ORACLE_HINTS) and len(raw_input) > 10:
            kind, severity, details = (
                "ORACLE_TOUCH",
                "Medium",
                "Possible oracle price update path in calldata",
            )

        if not kind:
            return None

        to_addr = tx.get("to")
        watched = store.list_watched()
        watched_on_chain = {w["address"].lower() for w in watched if w["chain"] == chain}
        # With watches on this chain: only emit if target matches; else network-wide sample
        if watched_on_chain and to_addr and str(to_addr).lower() not in watched_on_chain:
            return None

        return {
            "id": f"{kind}-{tx_hash_hex[:14]}",
            "timestamp": time.time(),
            "chain": chain,
            "block": block_num,
            "type": kind,
            "severity": severity,
            "tx_hash": tx_hash_hex,
            "from_address": tx.get("from"),
            "to_address": to_addr,
            "details": details,
        }

    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return store.recent_alerts(limit)


sentinel = Sentinel()
