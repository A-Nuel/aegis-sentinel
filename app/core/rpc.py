"""Multi-chain RPC with optional Alchemy/Infura + public failover.

Adapted from AegisWeb3 ProtoSec rpc_manager — secrets never hardcoded.
"""

from __future__ import annotations

import time
from typing import Any

import requests
from web3 import Web3
from web3.providers.rpc import HTTPProvider

from app.config import settings


class RPCManager:
    def __init__(self) -> None:
        self._clients: dict[str, Web3] = {}

    def endpoints(self, chain: str) -> list[tuple[str, str]]:
        chain = chain.lower().strip()
        alchemy = settings.alchemy_api_key
        infura = settings.infura_api_key
        public = {
            "ethereum": settings.eth_rpc_url,
            "arbitrum": settings.arb_rpc_url,
            "base": settings.base_rpc_url,
            "optimism": settings.opt_rpc_url,
            "polygon": settings.polygon_rpc_url,
        }.get(chain, settings.eth_rpc_url)

        ordered: list[tuple[str, str]] = []
        if alchemy:
            paths = {
                "ethereum": f"https://eth-mainnet.g.alchemy.com/v2/{alchemy}",
                "arbitrum": f"https://arb-mainnet.g.alchemy.com/v2/{alchemy}",
                "base": f"https://base-mainnet.g.alchemy.com/v2/{alchemy}",
                "optimism": f"https://opt-mainnet.g.alchemy.com/v2/{alchemy}",
                "polygon": f"https://polygon-mainnet.g.alchemy.com/v2/{alchemy}",
            }
            if chain in paths:
                ordered.append(("alchemy", paths[chain]))
        if infura:
            paths = {
                "ethereum": f"https://mainnet.infura.io/v3/{infura}",
                "arbitrum": f"https://arbitrum-mainnet.infura.io/v3/{infura}",
                "base": f"https://base-mainnet.infura.io/v3/{infura}",
                "optimism": f"https://optimism-mainnet.infura.io/v3/{infura}",
                "polygon": f"https://polygon-mainnet.infura.io/v3/{infura}",
            }
            if chain in paths:
                ordered.append(("infura", paths[chain]))
        ordered.append(("public", public))
        return ordered

    def ping(self, url: str) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            resp = requests.post(
                url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=3,
            )
            latency = (time.perf_counter() - start) * 1000
            data = resp.json()
            if resp.status_code == 200 and "result" in data:
                return {
                    "healthy": True,
                    "latency_ms": round(latency, 2),
                    "block": int(data["result"], 16),
                }
            return {"healthy": False, "latency_ms": round(latency, 2), "error": resp.text[:120]}
        except Exception as exc:
            return {
                "healthy": False,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "error": str(exc),
            }

    def health(self, chain: str) -> dict[str, Any]:
        for provider, url in self.endpoints(chain):
            res = self.ping(url)
            if res.get("healthy"):
                return {
                    "chain": chain,
                    "provider": provider,
                    "url": url,
                    "status": "HEALTHY",
                    **res,
                }
        return {"chain": chain, "status": "DOWN", "error": "all endpoints failed"}

    def get_web3(self, chain: str) -> Web3:
        health = self.health(chain)
        url = health.get("url") or self.endpoints(chain)[-1][1]
        if chain not in self._clients:
            self._clients[chain] = Web3(HTTPProvider(url, request_kwargs={"timeout": 15}))
        return self._clients[chain]


rpc = RPCManager()
