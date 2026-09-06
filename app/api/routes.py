from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.core.rpc import rpc
from app.engine.credits import credit_loop
from app.engine.explain import public_feed
from app.engine.mcp_agent import self_funding_status
from app.engine.sentinel import sentinel
from app.engine.tx_explain import explain_tx

router = APIRouter(prefix="/api")


class WatchRequest(BaseModel):
    address: str
    chain: str = "ethereum"
    label: str = ""


class UnwatchRequest(BaseModel):
    address: str
    chain: str = "ethereum"


class ExplainTxRequest(BaseModel):
    tx_hash: str
    chain: str = "ethereum"


@router.get("/alerts")
def alerts(limit: int = 50):
    return sentinel.recent_alerts(limit)


@router.get("/findings")
def findings(limit: int = 50):
    return public_feed(sentinel.recent_alerts(limit), limit=limit)


@router.get("/findings/{alert_id}")
def finding_detail(alert_id: str):
    for a in sentinel.recent_alerts(200):
        if a.get("id") == alert_id:
            from app.engine.explain import explain_alert

            return explain_alert(a)
    return {"error": "not found"}


@router.post("/explain-tx")
def explain_transaction(req: ExplainTxRequest):
    """Sibling: paste a tx hash → detector + Orbio-backed brief."""
    try:
        return explain_tx(req.tx_hash, req.chain)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/watched")
def watched():
    return sentinel.watched


@router.post("/watch")
def watch(req: WatchRequest):
    return sentinel.watch(req.address, req.chain, req.label)


@router.post("/unwatch")
def unwatch(req: UnwatchRequest):
    return {"removed": sentinel.unwatch(req.address, req.chain)}


@router.post("/scan")
def scan(chain: str = "ethereum", enrich: bool | None = None):
    if enrich is None:
        enrich = bool(settings.llm_api_key)
    return sentinel.scan_latest_block(chain, enrich=enrich)


@router.post("/scan/all")
def scan_all(enrich: bool | None = None):
    if enrich is None:
        enrich = bool(settings.llm_api_key)
    results = []
    total = 0
    for chain in settings.chains_list:
        r = sentinel.scan_latest_block(chain, enrich=enrich)
        total += int(r.get("new_alerts") or 0)
        results.append(r)
    return {"chains": settings.chains_list, "new_alerts": total, "results": results}


@router.get("/rpc/health")
def rpc_health(chain: str = "ethereum"):
    return rpc.health(chain)


@router.get("/credits")
def credits():
    return credit_loop.status()


@router.post("/credits/ensure")
def credits_ensure():
    return credit_loop.ensure_funded()


@router.get("/credits/key")
def credits_key():
    return credit_loop.gateway_key_info()


@router.get("/agent/self-funding")
def agent_self_funding():
    return self_funding_status()
