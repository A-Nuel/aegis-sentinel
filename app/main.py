from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.engine.sentinel import sentinel

app = FastAPI(
    title="Aegis Sentinel",
    version="0.1.0",
    description="Self-sustaining DeFi security agent for Orbio Build Week",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "service": "Aegis Sentinel",
        "watched": len(sentinel.watched),
        "alerts": len(sentinel.alerts),
    }
