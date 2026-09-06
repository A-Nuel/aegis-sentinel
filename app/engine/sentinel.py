"""Live-block threat sentinel for continuous DeFi monitoring."""

from __future__ import annotations

import time
from typing import Any

from web3 import Web3

from app.core.llm import llm
from app.core.rpc import rpc
from app.core.storage import store
from app.engine.detectors import classify_calldata

HIGH_TYPES = {
    "FLASH_LOAN",
    "ADMIN_STATE_CHANGE",
    "LENDING_ORACLE_RISK",
    "LENDING_LIQUIDATION",
}


class Sentinel:
    def watch(self, address: str, chain: str = "ethereum", label: str = "") -> dict[str, str]:
        addr = Web3.to_checksum_address(address)
        return store.add_watch(addr, chain.lower(), label or addr[:10])

    def unwatch(self, address: str, chain: str = "ethereum") -> bool:
        return store.remove_watch(Web3.to_checksum_address(address), chain.lower())

    @property
    def watched(self) -> list[dict[str, str]]:
        return store.list_watched()

    def _watched_set(self, chain: str) -> set[str]:
        return {w["address"].lower() for w in store.list_watched() if w["chain"] == chain}

    def scan_latest_block(self, chain: str = "ethereum", enrich: bool = True) -> dict[str, Any]:
        chain = chain.lower()
        new_alerts: list[dict[str, Any]] = []
        try:
            w3 = rpc.get_web3(chain)
            block = w3.eth.get_block("latest", full_transactions=True)
            block_num = int(block["number"])
            txs = list(block.get("transactions") or [])
            watched = self._watched_set(chain)

            prioritized: list[Any] = []
            rest: list[Any] = []
            for tx in txs:
                to_addr = str(tx.get("to") or "").lower()
                frm = str(tx.get("from") or "").lower()
                if watched and (to_addr in watched or frm in watched):
                    prioritized.append(tx)
                else:
                    rest.append(tx)
            ordered = prioritized + rest[:80]

            for tx in ordered:
                alert = self._inspect_tx(w3, chain, block_num, tx, watched)
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

    def _inspect_tx(
        self,
        w3: Web3,
        chain: str,
        block_num: int,
        tx: Any,
        watched: set[str],
    ) -> dict[str, Any] | None:
        raw_input = str(tx.get("input") or "")
        tx_hash = tx.get("hash")
        tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        value_eth = float(w3.from_wei(tx.get("value") or 0, "ether"))
        to_addr = tx.get("to")
        from_addr = tx.get("from")
        to_l = str(to_addr or "").lower()
        from_l = str(from_addr or "").lower()
        on_watch = bool(watched) and (to_l in watched or from_l in watched)

        hit = classify_calldata(raw_input, value_eth)
        if not hit:
            return None

        if (
            watched
            and not on_watch
            and hit["type"] not in HIGH_TYPES
            and hit["type"] != "WHALE_TRANSFER"
        ):
            return None

        return {
            "id": f"{hit['type']}-{tx_hash_hex[:14]}",
            "timestamp": time.time(),
            "chain": chain,
            "block": block_num,
            "type": hit["type"],
            "severity": hit["severity"],
            "tx_hash": tx_hash_hex,
            "from_address": from_addr,
            "to_address": to_addr,
            "watched_hit": on_watch,
            "details": hit["details"] + (" · watched target" if on_watch else ""),
        }

    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return store.recent_alerts(limit)


sentinel = Sentinel()
