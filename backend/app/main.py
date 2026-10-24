"""Fathom backend — FastAPI application entrypoint.

Advisory ocean decision copilot API. Deterministic engine logic lives under
``engine/``; the LLM agent under ``agent/`` only orchestrates and explains.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, layers, meta

# Frontend dev server (Vite). Add deployed origins here as needed.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

app = FastAPI(
    title="Fathom API",
    description="Advisory ocean decision copilot for the Massachusetts working waterfront.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
