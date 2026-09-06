"""Deeper calldata detectors including lending / oracle-risk heuristics.

Defensive classification only — signals risk patterns, not how to attack.
"""

from __future__ import annotations

from typing import Any

# 4-byte selectors (lowercase, no 0x)
FLASH = {
    "5cffe9de",  # flashLoanSimple
    "ab9c4b5d",  # flashLoan (Aave-style)
    "f04f2707",
}
FLASH_SUB = ("flashloan", "flashloan")

ADMIN = {
    "f2fde38b",  # transferOwnership
    "715018a6",  # renounceOwnership
    "8456cb59",  # pause
    "3f4ba83a",  # unpause
    "3659cfe6",  # upgradeTo
    "4f1ef286",  # upgradeToAndCall
    "2f2ff15d",  # grantRole
    "d547741f",  # revokeRole
}

ORACLE = {
    "66ad5c8a",
    "8d6cc56d",
}
ORACLE_SUB = ("setprice", "updateprice", "submitvalue", "latestanswer", "setfeed", "setoracle")

# Lending / money-market style entrypoints (Aave / Compound-family patterns)
LENDING_BORROW = {
    "a415bcad",  # borrow
    "c5ebeaec",  # borrow (Compound-style)
}
LENDING_SUPPLY = {
    "617ba037",  # supply
    "a0712d68",  # mint (cToken)
}
LENDING_WITHDRAW = {
    "69328dec",  # withdraw
    "db006a75",  # redeem
    "852a12e3",  # redeemUnderlying-ish
}
LENDING_REPAY = {
    "573ade81",  # repay
    "0e752702",  # liquidateBorrow (Compound)
}
LENDING_LIQUIDATE = {
    "00a718a9",  # liquidationCall (Aave)
    "f5e3c462",
    "0e752702",
}

LIQUIDITY = {
    "02751cec",  # removeLiquidityETH
    "af2979eb",
    "ded9382a",
    "2195995c",
    "baa2abde",  # removeLiquidity
}

APPROVAL = {
    "095ea7b3",  # approve
    "d505accf",  # permit
}

SWAP = {
    "38ed1739",
    "7ff36ab5",
    "18cbafe5",
    "5c11d795",
    "414bf389",
    "c04b8d59",
    "db3e2198",
}


def _sel(raw_input: str) -> str:
    s = (raw_input or "").lower()
    if s.startswith("0x"):
        s = s[2:]
    return s[:8] if len(s) >= 8 else s


def _contains_any(raw: str, selectors: set[str]) -> bool:
    # selectors may appear as top-level or nested in multicall payloads
    return any(sel in raw for sel in selectors)


def classify_calldata(raw_input: str, value_native: float) -> dict[str, Any] | None:
    raw = (raw_input or "").lower()
    if raw.startswith("0x"):
        raw_body = raw[2:]
    else:
        raw_body = raw
    sel = _sel(raw)

    has_flash = sel in FLASH or "flashloan" in raw_body or _contains_any(raw_body, FLASH)
    has_borrow = sel in LENDING_BORROW or _contains_any(raw_body, LENDING_BORROW)
    has_liq = sel in LENDING_LIQUIDATE or _contains_any(raw_body, LENDING_LIQUIDATE)
    has_oracle = sel in ORACLE or any(x in raw_body for x in ORACLE_SUB) or _contains_any(
        raw_body, ORACLE
    )
    has_swap = sel in SWAP or _contains_any(raw_body, SWAP)
    has_remove_liq = sel in LIQUIDITY or _contains_any(raw_body, LIQUIDITY)

    # Combination: classic lending-oracle stress pattern (same tx)
    if has_flash and (has_borrow or has_liq):
        return {
            "type": "LENDING_ORACLE_RISK",
            "severity": "Critical",
            "details": (
                "Same-tx pattern: flash-loan + borrow/liquidate selectors "
                "(common in oracle/pricing stress on lending markets)"
            ),
        }

    if has_flash and has_oracle:
        return {
            "type": "LENDING_ORACLE_RISK",
            "severity": "Critical",
            "details": "Flash-loan path combined with oracle/price-update style calldata",
        }

    if has_oracle and (has_borrow or has_liq):
        return {
            "type": "LENDING_ORACLE_RISK",
            "severity": "High",
            "details": "Oracle/price-style call collocated with borrow or liquidate selectors",
        }

    if has_flash and has_swap and has_remove_liq:
        return {
            "type": "LENDING_ORACLE_RISK",
            "severity": "High",
            "details": "Flash + swap + remove-liquidity selectors in one payload (pool skew risk)",
        }

    if has_flash:
        return {
            "type": "FLASH_LOAN",
            "severity": "High",
            "details": f"Flash-loan selector/pattern (0x{sel})",
        }

    if sel in ADMIN:
        label = {
            "f2fde38b": "transferOwnership",
            "715018a6": "renounceOwnership",
            "8456cb59": "pause",
            "3f4ba83a": "unpause",
            "3659cfe6": "upgradeTo",
            "4f1ef286": "upgradeToAndCall",
            "2f2ff15d": "grantRole",
            "d547741f": "revokeRole",
        }.get(sel, "admin/upgrade")
        return {
            "type": "ADMIN_STATE_CHANGE",
            "severity": "High",
            "details": f"Privileged call: {label} (0x{sel})",
        }

    if has_oracle:
        return {
            "type": "ORACLE_TOUCH",
            "severity": "Medium",
            "details": f"Oracle/price-update pattern (0x{sel})",
        }

    if sel in LENDING_LIQUIDATE or has_liq:
        return {
            "type": "LENDING_LIQUIDATION",
            "severity": "Medium",
            "details": f"Lending liquidation-style selector (0x{sel})",
        }

    if sel in LENDING_BORROW or has_borrow:
        sev = "Medium" if value_native >= 10 else "Low"
        return {
            "type": "LENDING_BORROW",
            "severity": sev,
            "details": f"Lending borrow-style selector (0x{sel})",
        }

    if sel in LENDING_SUPPLY:
        return {
            "type": "LENDING_SUPPLY",
            "severity": "Low",
            "details": f"Lending supply/mint-style selector (0x{sel})",
        }

    if sel in LENDING_WITHDRAW:
        return {
            "type": "LENDING_WITHDRAW",
            "severity": "Low",
            "details": f"Lending withdraw/redeem-style selector (0x{sel})",
        }

    if has_remove_liq:
        return {
            "type": "LIQUIDITY_REMOVE",
            "severity": "Medium",
            "details": f"Remove-liquidity style selector 0x{sel}",
        }

    if sel in APPROVAL and "ffffffffffffffffffffffffffffffffffffffff" in raw_body:
        return {
            "type": "UNLIMITED_APPROVAL",
            "severity": "Medium",
            "details": "approve/permit with max-uint-style allowance",
        }

    if value_native >= 500:
        extra = " + swap/router calldata" if has_swap else ""
        return {
            "type": "WHALE_TRANSFER",
            "severity": "Medium",
            "details": f"{value_native:,.2f} native transferred{extra}",
        }

    if value_native >= 50 and has_swap:
        return {
            "type": "LARGE_SWAP",
            "severity": "Low",
            "details": f"Router swap with {value_native:,.2f} native attached",
        }

    return None
