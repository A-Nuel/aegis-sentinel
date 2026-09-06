"""Deeper calldata detectors.

Uses well-known 4-byte selectors (not just string hints).
Defensive classification only — no exploit construction.
"""

from __future__ import annotations

from typing import Any

# 4-byte selectors (lowercase, no 0x)
FLASH = {
    "5cffe9de",  # flashLoanSimple(address,uint256,bytes)
    "ab9c4b5d",  # flashLoan(address,address[],uint256[],bytes)
    "f04f2707",  # often seen on some balancer-style flashes
    "5c60da1b",  # not flash — skip
}
# Keep extra substrings for encoded inner calls
FLASH_SUB = ("flashloan", "flashLoan")

ADMIN = {
    "f2fde38b",  # transferOwnership(address)
    "715018a6",  # renounceOwnership()
    "8456cb59",  # pause()
    "3f4ba83a",  # unpause()
    "2f2770db",  # pause variants sometimes differ
    "3659cfe6",  # upgradeTo(address)  transparent proxy
    "4f1ef286",  # upgradeToAndCall(address,bytes)
    "d1f57894",  # upgradeToAndCall (some impls)
    "2f2ff15d",  # grantRole(bytes32,address)
    "d547741f",  # revokeRole(bytes32,address)
    "8c18ad66",  # setAdmin-like custom — keep as extra substr
}

ORACLE = {
    "66ad5c8a",  # various setPrice
    "8d6cc56d",  # updatePrice loosely
}
ORACLE_SUB = ("setprice", "updateprice", "submitvalue", "latestanswer", "setfeed")

LIQUIDITY = {
    "baa2abde",  # Uniswap V2 swap(uint256,uint256,address,bytes) wait that's swap
    "02751cec",  # removeLiquidityETH
    "af2979eb",  # removeLiquidityETHSupportingFeeOnTransferTokens
    "ded9382a",  # removeLiquidityETHWithPermit
    "2195995c",  # removeLiquidityWithPermit
    "baa2abde",  # removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)
}

APPROVAL = {
    "095ea7b3",  # approve(address,uint256)
    "d505accf",  # permit(address,address,uint256,uint256,uint8,bytes32,bytes32)
}

SWAP = {
    "38ed1739",  # swapExactTokensForTokens
    "7ff36ab5",  # swapExactETHForTokens
    "18cbafe5",  # swapExactTokensForETH
    "5c11d795",  # swapExactTokensForTokensSupportingFeeOnTransferTokens
    "414bf389",  # exactInputSingle (uni v3)
    "c04b8d59",  # exactInput
    "db3e2198",  # exactOutput
}

# ERC-20 transfer
TRANSFER = {"a9059cbb", "23b872dd"}  # transfer, transferFrom


def _sel(raw_input: str) -> str:
    s = raw_input.lower()
    if s.startswith("0x"):
        s = s[2:]
    return s[:8] if len(s) >= 8 else s


def classify_calldata(raw_input: str, value_native: float) -> dict[str, Any] | None:
    raw = (raw_input or "").lower()
    sel = _sel(raw)

    if sel in FLASH or any(x.lower() in raw for x in FLASH_SUB):
        return {
            "type": "FLASH_LOAN",
            "severity": "High",
            "details": f"Flash-loan selector/pattern ({sel})",
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

    if sel in ORACLE or any(x in raw for x in ORACLE_SUB):
        return {
            "type": "ORACLE_TOUCH",
            "severity": "Medium",
            "details": f"Oracle/price-update pattern (0x{sel})",
        }

    if sel in LIQUIDITY:
        return {
            "type": "LIQUIDITY_REMOVE",
            "severity": "Medium",
            "details": f"Remove-liquidity style selector 0x{sel}",
        }

    # Unlimited approval heuristic: approve with amount ~ max uint in tail of calldata
    if sel in APPROVAL and "ffffffffffffffffffffffffffffffffffffffff" in raw:
        return {
            "type": "UNLIMITED_APPROVAL",
            "severity": "Medium",
            "details": "approve/permit with max-uint-style allowance",
        }

    if value_native >= 500:
        extra = " + swap/router calldata" if sel in SWAP else ""
        return {
            "type": "WHALE_TRANSFER",
            "severity": "Medium",
            "details": f"{value_native:,.2f} native transferred{extra}",
        }

    if value_native >= 50 and sel in SWAP:
        return {
            "type": "LARGE_SWAP",
            "severity": "Low",
            "details": f"Router swap with {value_native:,.2f} native attached",
        }

    return None
