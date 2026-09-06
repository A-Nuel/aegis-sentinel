from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.engine.sentinel import sentinel

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Aegis Sentinel",
    version="0.3.0",
    description="Continuous DeFi security agent — public findings + self-funding design",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def home():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"service": "Aegis Sentinel", "docs": "/docs"}


@app.get("/health")
def health():
    return {
        "status": "ONLINE",
        "service": "Aegis Sentinel",
        "version": "0.3.0",
        "watched": len(sentinel.watched),
        "alerts": len(sentinel.recent_alerts(5)),
    }
