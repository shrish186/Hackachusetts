"""Liveness (/api/health) and readiness (/api/ready) endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api import warmup

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: answers immediately, even during warm-up (Render health check)."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    """Readiness: 200 once the basic warm-up is done; the wide warm-up continues in the background."""
    s = warmup.status()  # a dict copy: no work happens here
    if s["ready"]:
        return JSONResponse({"status": "ready", "warmup_seconds": s["seconds"],
                             "full_warmup": "done" if s.get("full_ready") else "running",
                             "full_warmup_seconds": s.get("full_seconds")})
    body = {"status": "warming_up" if not s["error"] else "warmup_failed"}
    return JSONResponse(body, status_code=503, headers={"Retry-After": "5"})
