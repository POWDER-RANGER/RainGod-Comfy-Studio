"""RainGod Comfy Studio — FastAPI entry point.

Wires together:
  - Existing RAINGOD backend (rain_backend.py endpoints)
  - New dispatch router (/dispatch, /dispatch/status)
  - Static file serving for the node-graph UI

Start:
  uvicorn backend.main:app --reload --port 8000

Or via start_all.sh / start_all.ps1 (which handles ComfyUI + backend together).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ── Logging setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO"), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── CORS ───────────────────────────────────────────────────────────
_raw = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw.split(",") if o.strip()]
    if _raw.strip()
    else ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:8000"]
)


# ── Lifespan ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: warm the dispatcher (validates env, lazy-loads adapters).
    Adapters only import if their env key is set — safe to start with 0 keys.
    """
    from .dispatcher import RainGodDispatcher
    application.state.dispatcher = RainGodDispatcher()
    application.state.dispatcher._init_adapters()

    status = application.state.dispatcher.status()
    active = [k for k, v in status.items() if v]
    logger.info("RainGod Studio started — active adapters: %s", active)
    yield
    logger.info("RainGod Studio shutting down")


# ── App ────────────────────────────────────────────────────────────
app = FastAPI(
    title="RainGod Comfy Studio",
    description="Node-based AI creative pipeline — local Ollama + free cloud GPU fleet",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────

# 1. Dispatch router — /dispatch and /dispatch/status
from .dispatch_routes import router as dispatch_router
app.include_router(dispatch_router)

# 2. Original RAINGOD ComfyUI backend — /generate, /batch-generate, /health, etc.
try:
    from .rain_backend import app as _rain_app
    for route in _rain_app.routes:
        app.routes.append(route)
    logger.info("RAINGOD ComfyUI routes mounted")
except Exception as e:
    logger.warning("Could not mount rain_backend routes: %s", e)


# ── Static UI serving ──────────────────────────────────────────────
_SWITCHBOARD = Path(__file__).parent.parent / "switchboard"

if _SWITCHBOARD.exists():
    app.mount("/ui", StaticFiles(directory=_SWITCHBOARD, html=True), name="switchboard")

    @app.get("/", include_in_schema=False)
    async def root_ui() -> FileResponse:
        """Serve the node-graph studio at the root URL."""
        return FileResponse(_SWITCHBOARD / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root_no_ui() -> dict:
        return {
            "name": "RainGod Comfy Studio API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "dispatch": "/dispatch",
            "note": "switchboard/index.html not found — open it directly in a browser",
        }


# ── Unified health ─────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Lightweight health check — does NOT hit ComfyUI or cloud services."""
    try:
        status = app.state.dispatcher.status()
    except AttributeError:
        status = {}
    return {"status": "ok", "adapters": status}
