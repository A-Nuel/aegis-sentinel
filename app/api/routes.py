from fastapi import APIRouter
from pydantic import BaseModel

from app.core.rpc import rpc
from app.engine.credits import credit_loop
from app.engine.sentinel import sentinel

router = APIRouter(prefix="/api")


class WatchRequest(BaseModel):
    address: str
    chain: str = "ethereum"
    label: str = ""


class UnwatchRequest(BaseModel):
    address: str
    chain: str = "ethereum"


@router.get("/alerts")
def alerts(limit: int = 50):
    return sentinel.recent_alerts(limit)


@router.get("/watched")
def watched():
    return sentinel.watched


@router.post("/watch")
def watch(req: WatchRequest):
    return sentinel.watch(req.address, req.chain, req.label)


@router.post("/unwatch")
def unwatch(req: UnwatchRequest):
    ok = sentinel.unwatch(req.address, req.chain)
    return {"removed": ok}


@router.post("/scan")
def scan(chain: str = "ethereum", enrich: bool = True):
    return sentinel.scan_latest_block(chain, enrich=enrich)


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
    return credit_loop.openrouter_key_info()
