"""Plain-language meaning + general defensive guidance for alerts."""

from __future__ import annotations

from typing import Any

GUIDANCE: dict[str, dict[str, str]] = {
    "FLASH_LOAN": {
        "title": "Flash-loan style activity",
        "means": (
            "A transaction looks like it borrows a large amount for one block, "
            "does work, then repays. Common in complex DeFi and in many historical exploits."
        ),
        "watch_for": (
            "Same-tx interaction with a protocol you care about, pool imbalance, "
            "or oracle reads right after a huge borrow."
        ),
        "harden": (
            "Resistant oracles, reentrancy guards, access control, caps/pauses. "
            "Do not trust spot prices that can move inside one transaction."
        ),
    },
    "WHALE_TRANSFER": {
        "title": "Large native transfer",
        "means": "A very large amount of the chain's native token moved in one transfer.",
        "watch_for": "Follow-on swaps into thin pools or repeated inflows to one contract.",
        "harden": "Withdrawal limits, delay queues, and monitoring on treasury addresses.",
    },
    "LARGE_SWAP": {
        "title": "Large router swap",
        "means": "A DEX router swap with a sizable native value attached.",
        "watch_for": "Price impact on thin pairs tied to a protocol you watch.",
        "harden": "TWAP/resistant pricing and circuit breakers on abnormal volume.",
    },
    "ADMIN_STATE_CHANGE": {
        "title": "Admin / pause / upgrade / role change",
        "means": (
            "Calldata matches pause, ownership, proxy upgrade, or AccessControl roles. "
            "A privileged key likely changed system state."
        ),
        "watch_for": "Unexpected pauses, new owners/implementations, or role grants off-schedule.",
        "harden": "Multisig + timelock for admin and upgrades; alert on every ownership/role event.",
    },
    "ORACLE_TOUCH": {
        "title": "Possible oracle / price update",
        "means": "Calldata hints at price submission or feed update logic.",
        "watch_for": "Sharp price jumps or updates tightly coupled to borrow/mint in the same block.",
        "harden": "Decentralized or time-weighted feeds and deviation circuit breakers.",
    },
    "LIQUIDITY_REMOVE": {
        "title": "Liquidity removal pattern",
        "means": "Call looks like LP tokens being burned / liquidity pulled from a pool.",
        "watch_for": "Sudden depth drop on a pair your protocol uses as pricing or collateral.",
        "harden": "Don't treat momentary pool depth as a safe valuation; use caps and TWAPs.",
    },
    "UNLIMITED_APPROVAL": {
        "title": "Unlimited token approval",
        "means": "An approve/permit appears to set allowance to max uint.",
        "watch_for": "Approvals to unknown spenders; later drains via transferFrom.",
        "harden": "Exact allowances, permit deadlines, regular allowance reviews.",
    },
    "SCAN_ERROR": {
        "title": "Scanner error",
        "means": "The agent failed to read a block or RPC endpoint.",
        "watch_for": "Repeated errors on one chain.",
        "harden": "Add failover RPCs or switch providers.",
    },
}


def explain_alert(alert: dict[str, Any]) -> dict[str, Any]:
    kind = str(alert.get("type") or "")
    base = GUIDANCE.get(
        kind,
        {
            "title": kind or "Event",
            "means": alert.get("llm_summary") or alert.get("details") or "Detected on-chain event.",
            "watch_for": "Correlate with protocol-specific state if this address matters to you.",
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
        "watched_hit": alert.get("watched_hit"),
        "public": True,
        **base,
    }


def public_feed(alerts: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    return [explain_alert(a) for a in alerts[:limit]]
