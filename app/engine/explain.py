"""Plain-language meaning + general defensive guidance for alerts.

Educational / defensive only — no exploit steps.
"""

from __future__ import annotations

from typing import Any

GUIDANCE: dict[str, dict[str, str]] = {
    "FLASH_LOAN": {
        "title": "Flash-loan style activity",
        "means": (
            "A transaction looks like it borrows a large amount for one block, "
            "does work, then repays. That pattern is common in complex DeFi "
            "strategies and also in many historical exploits."
        ),
        "watch_for": (
            "Unexpected interaction with your protocol in the same transaction, "
            "sudden pool imbalance, or oracle reads right after a huge borrow."
        ),
        "harden": (
            "Prefer TWAP/resistant oracles, reentrancy guards, proper access "
            "control on privileged functions, and economic limits (caps, pauses). "
            "Review integrations that assume spot prices cannot move in one tx."
        ),
    },
    "WHALE_TRANSFER": {
        "title": "Large native transfer",
        "means": (
            "A very large amount of the chain's native token moved in one transfer. "
            "Alone it is not an exploit; it can signal liquidations, OTC, or preparation for market moves."
        ),
        "watch_for": (
            "Follow-on swaps into thin pools, governance token dumps, or repeated "
            "large inflows to a single contract you care about."
        ),
        "harden": (
            "For protocols: withdrawal limits, delay queues, and monitoring on "
            "treasury addresses. For users: size positions relative to pool depth."
        ),
    },
    "ADMIN_STATE_CHANGE": {
        "title": "Admin / pause / ownership pattern",
        "means": (
            "Calldata resembles pause, unpause, or ownership transfer. That usually "
            "means a privileged key changed system state."
        ),
        "watch_for": (
            "Unexpected pauses, new owner addresses, or renounce/transfer without "
            "a published ops schedule."
        ),
        "harden": (
            "Use multisig + timelock for admin, document emergency procedures, "
            "restrict who can pause, and alert on any ownership event."
        ),
    },
    "ORACLE_TOUCH": {
        "title": "Possible oracle / price update path",
        "means": (
            "Calldata hints at price submission or oracle update logic. Oracles are "
            "a common attack surface when protocols trust a single spot update."
        ),
        "watch_for": (
            "Sharp price jumps, single-source feeds, or updates tightly coupled to "
            "borrow/mint in the same block."
        ),
        "harden": (
            "Use decentralized or time-weighted feeds, circuit breakers on deviation, "
            "and avoid under-collateralized borrows against manipulable spot prices."
        ),
    },
    "SCAN_ERROR": {
        "title": "Scanner error",
        "means": "The agent failed to read a block or RPC endpoint (network/RPC issue).",
        "watch_for": "Repeated errors on one chain.",
        "harden": "Add failover RPCs, raise rate limits, or switch providers.",
    },
}


def explain_alert(alert: dict[str, Any]) -> dict[str, Any]:
    kind = str(alert.get("type") or "")
    base = GUIDANCE.get(
        kind,
        {
            "title": kind or "Event",
            "means": alert.get("llm_summary") or alert.get("details") or "Detected on-chain event.",
            "watch_for": "Correlate with protocol-specific state if this address is critical to you.",
            "harden": "Keep monitoring, least-privilege admin, and tested incident response.",
        },
    )
    return {
        "id": alert.get("id"),
        "type": kind,
        "severity": alert.get("severity"),
        "chain": alert.get("chain"),
        "tx_hash": alert.get("tx_hash"),
        "block": alert.get("block"),
        "raw_details": alert.get("details"),
        "llm_summary": alert.get("llm_summary"),
        "public": True,
        **base,
    }


def public_feed(alerts: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    out = []
    for a in alerts[:limit]:
        # Strip anything that could look like secrets; alerts are already public-chain data
        out.append(explain_alert(a))
    return out
