"""Live-block threat sentinel adapted from AegisWeb3 ProtoSec."""

from __future__ import annotations

import time
from typing import Any

from web3 import Web3

from app.config import settings

FLASH_SIGS = ("ab963c34", "5cffe9de", "flashloan")
ADMIN_HINTS = ("845dd321", "f2fde38b", "pause(", "transferownership")


class Sentinel:
    def __init__(self) -> None:
        self.alerts: list[dict[str, Any]] = []
        self.watched: list[dict[str, str]] = []
        self._w3: dict[str, Web3] = {}

    def _rpc(self, chain: str) -> str:
        return {
            "ethereum": settings.eth_rpc_url,
            "arbitrum": settings.arb_rpc_url,
            "base": settings.base_rpc_url,
        }.get(chain, settings.eth_rpc_url)

    def web3(self, chain: str) -> Web3:
        if chain not in self._w3:
            self._w3[chain] = Web3(Web3.HTTPProvider(self._rpc(chain)))
        return self._w3[chain]

    def watch(self, address: str, chain: str = "ethereum", label: str = "") -> dict[str, str]:
        item = {
            "address": Web3.to_checksum_address(address),
            "chain": chain,
            "label": label or address[:10],
        }
        if item not in self.watched:
            self.watched.append(item)
        return item

    def scan_latest_block(self, chain: str = "ethereum") -> dict[str, Any]:
        new_alerts: list[dict[str, Any]] = []
        try:
            w3 = self.web3(chain)
            block = w3.eth.get_block("latest", full_transactions=True)
            block_num = int(block["number"])
            for tx in list(block.get("transactions") or [])[:25]:
                alert = self._inspect_tx(w3, chain, block_num, tx)
                if alert:
                    new_alerts.append(alert)
                    self.alerts.append(alert)
        except Exception as exc:
            new_alerts.append(
                {
                    "id": f"ERR-{int(time.time())}",
                    "timestamp": time.time(),
                    "chain": chain,
                    "type": "SCAN_ERROR",
                    "severity": "Low",
                    "details": str(exc),
                }
            )
        return {"chain": chain, "new_alerts": len(new_alerts), "alerts": new_alerts}

    def _inspect_tx(self, w3: Web3, chain: str, block_num: int, tx: Any) -> dict[str, Any] | None:
        raw_input = str(tx.get("input") or "").lower()
        tx_hash = tx.get("hash")
        tx_hash_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
        value_eth = float(w3.from_wei(tx.get("value") or 0, "ether"))
        kind = None
        severity = "Medium"
        details = ""

        if any(sig in raw_input for sig in FLASH_SIGS):
            kind, severity, details = "FLASH_LOAN", "High", "Flash-loan signature in calldata"
        elif value_eth >= 500:
            kind, severity, details = "WHALE_TRANSFER", "Medium", f"{value_eth:,.2f} ETH moved"
        elif any(h in raw_input for h in ADMIN_HINTS):
            kind, severity, details = "ADMIN_STATE_CHANGE", "High", "pause or ownership-style call"

        if not kind:
            return None

        to_addr = tx.get("to")
        watched_addrs = {w["address"].lower() for w in self.watched if w["chain"] == chain}
        if watched_addrs and to_addr and str(to_addr).lower() not in watched_addrs:
            return None

        return {
            "id": f"{kind}-{tx_hash_hex[:12]}",
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
        return list(reversed(self.alerts[-limit:]))


sentinel = Sentinel()
