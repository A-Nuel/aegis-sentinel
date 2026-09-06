from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.rpc import rpc
from app.engine.credits import credit_loop
from app.engine.sentinel import sentinel

router = APIRouter(prefix="/api")


class WatchRequest(BaseModel):
    address: str
    chain: str = "ethereum"
    label: str = ""


@router.get("/alerts")
def alerts(limit: int = 50):
    return sentinel.recent_alerts(limit)


@router.get("/watched")
def watched():
    return sentinel.watched


@router.post("/watch")
def watch(req: WatchRequest):
    return sentinel.watch(req.address, req.chain, req.label)


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
