"""Fathom backend — FastAPI application entrypoint.

Advisory ocean decision copilot API. Deterministic engine logic lives under
``engine/``; the agent under ``agent/`` only orchestrates and explains.

Env:
  FATHOM_DEMO_MODE        default "true": serve bundled snapshots only.
  FATHOM_ALLOWED_ORIGINS  comma-separated CORS origins (default http://localhost:5173).
"""
from __future__ import annotations

import os

os.environ.setdefault("FATHOM_DEMO_MODE", "true")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api import health, layers, meta  # noqa: E402
from app.api.security import HardeningMiddleware, allowed_origins, install_error_handlers  # noqa: E402

app = FastAPI(
    title="Fathom API",
    description="Advisory ocean decision copilot for the Massachusetts working waterfront.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
# Added last so it is the outermost layer (rate limit, size cap, timeout, headers).
app.add_middleware(HardeningMiddleware)
install_error_handlers(app)

# --- Routers -----------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
