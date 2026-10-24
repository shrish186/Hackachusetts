"""Fathom backend — FastAPI application entrypoint.

Advisory ocean decision copilot API. Deterministic engine logic lives under
``engine/``; the agent under ``agent/`` only orchestrates and explains.

Env:
  FATHOM_DEMO_MODE        default "true": serve bundled snapshots only.
  FATHOM_ALLOWED_ORIGINS  comma-separated CORS origins (default http://localhost:5173).
  FATHOM_TRUST_PROXY      "true" behind Render's HTTPS proxy (client IP + HSTS).
  FATHOM_ENABLE_DOCS      "true" to serve /docs, /redoc, /openapi.json (off in production).
  FATHOM_SKIP_WARMUP      "true" to skip the startup warm-up thread (tests).
"""
from __future__ import annotations

import os

os.environ.setdefault("FATHOM_DEMO_MODE", "true")

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api import health, layers, meta, ports, sim, trip  # noqa: E402
from app.api.security import (  # noqa: E402
    CORS_HEADERS,
    CORS_METHODS,
    HardeningMiddleware,
    allowed_origins,
    docs_enabled,
    install_error_handlers,
)
from app.api.warmup import start_warmup  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm up in a background thread so /api/health answers at once.
    start_warmup()
    yield


_DOCS = docs_enabled()
app = FastAPI(
    title="Fathom API",
    description="Advisory ocean decision copilot for the Massachusetts working waterfront.",
    version="0.3.0",
    docs_url="/docs" if _DOCS else None,
    redoc_url="/redoc" if _DOCS else None,
    openapi_url="/openapi.json" if _DOCS else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
    max_age=600,
)
# Added last so it is the outermost layer (rate limit, size cap, timeout, headers).
app.add_middleware(HardeningMiddleware)
install_error_handlers(app)

# --- Routers -----------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(ports.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
app.include_router(sim.router, prefix="/api")
app.include_router(trip.router, prefix="/api")
