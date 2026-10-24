"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a simple liveness signal for monitoring and smoke tests."""
    return {"status": "ok"}
