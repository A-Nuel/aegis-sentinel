from fastapi import APIRouter
from pydantic import BaseModel

from app.engine.sentinel import sentinel
from app.engine.credits import credit_loop

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
def scan(chain: str = "ethereum"):
    return sentinel.scan_latest_block(chain)


@router.get("/credits")
def credits():
    return credit_loop.status()
