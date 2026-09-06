"""Sibling feature: explain a single tx hash using detectors + optional Orbio LLM."""

from __future__ import annotations

from typing import Any

from web3 import Web3

from app.core.llm import llm
from app.core.rpc import rpc
from app.engine.detectors import classify_calldata
from app.engine.explain import explain_alert


def explain_tx(tx_hash: str, chain: str = "ethereum") -> dict[str, Any]:
    chain = chain.lower()
    w3 = rpc.get_web3(chain)
    h = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
    tx = w3.eth.get_transaction(h)
    value_eth = float(w3.from_wei(tx.get("value") or 0, "ether"))
    raw_input = str(tx.get("input") or "")
    hit = classify_calldata(raw_input, value_eth) or {
        "type": "UNKNOWN",
        "severity": "Low",
        "details": "No high-risk detector matched; still summarizing with LLM if key present.",
    }
    alert = {
        "id": f"TX-{h[:14]}",
        "type": hit["type"],
        "severity": hit["severity"],
        "details": hit["details"],
        "chain": chain,
        "tx_hash": h,
        "from_address": tx.get("from"),
        "to_address": tx.get("to"),
        "value_native": value_eth,
    }
    scored = llm.score_alert(alert)
    alert["llm_summary"] = scored.get("summary", "")
    alert["severity"] = scored.get("severity", alert["severity"])
    alert["llm_source"] = scored.get("source", "")
    out = explain_alert(alert)
    out["from_address"] = alert["from_address"]
    out["to_address"] = alert["to_address"]
    out["value_native"] = value_eth
    return out
