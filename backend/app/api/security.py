"""HTTP hardening for the Fathom API (Lane B, task 4).

Pure ASGI middleware (no extra dependencies):

* per-IP rate limit, 60 requests per 60 s, in memory
* 1 MB request body cap
* security headers on every response
* 20 s request timeout
* generic JSON errors with no stack traces

Settings come from env vars so Render and tests can change them.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("fathom.security")

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

MAX_BODY_BYTES = 1_000_000
RATE_LIMIT = int(os.getenv("FATHOM_RATE_LIMIT_PER_MIN", "60"))
RATE_WINDOW_S = 60.0
REQUEST_TIMEOUT_S = float(os.getenv("FATHOM_REQUEST_TIMEOUT_S", "20"))

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
]


def allowed_origins() -> list[str]:
    """CORS origins from FATHOM_ALLOWED_ORIGINS (comma-separated)."""
    raw = os.getenv("FATHOM_ALLOWED_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


async def _send_json(send: Send, status: int, body: dict[str, Any], extra: list[tuple[bytes, bytes]] | None = None) -> None:
    payload = json.dumps(body).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]
    headers += SECURITY_HEADERS + (extra or [])
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": payload})


class RateLimiter:
    """Sliding-window counter per client key, kept in memory."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] >= self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        if len(self._hits) > 10_000:  # bound memory under many distinct IPs
            for k in [k for k, v in self._hits.items() if not v][:5_000]:
                del self._hits[k]
        return True


def _client_ip(scope: Scope) -> str:
    """Client IP for rate limiting.

    Behind a trusted proxy (FATHOM_TRUST_PROXY=true, e.g. Render) use the LAST
    X-Forwarded-For hop, which the proxy appends; earlier hops are
    client-controlled and could be spoofed to dodge the limit.
    """
    if os.getenv("FATHOM_TRUST_PROXY", "false").lower() in {"1", "true", "yes"}:
        for name, value in scope.get("headers") or []:
            if name == b"x-forwarded-for":
                last = value.decode("latin-1").split(",")[-1].strip()
                if last:
                    return last
    client = scope.get("client")
    return client[0] if client else "unknown"


class HardeningMiddleware:
    """Rate limit, body cap, timeout and security headers in one ASGI layer."""

    def __init__(self, app: ASGIApp, limiter: RateLimiter | None = None) -> None:
        self.app = app
        self.limiter = limiter or RateLimiter(RATE_LIMIT, RATE_WINDOW_S)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path != "/api/health" and scope.get("method") != "OPTIONS":
            if not self.limiter.allow(_client_ip(scope)):
                await _send_json(send, 429, {"error": "Too many requests. Try again in a minute."}, [(b"retry-after", b"60")])
                return

        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                if int(declared) > MAX_BODY_BYTES:
                    await _send_json(send, 413, {"error": "Request body too large (max 1 MB)."})
                    return
            except ValueError:
                await _send_json(send, 400, {"error": "Bad request."})
                return

        received = 0

        async def capped_receive() -> dict[str, Any]:
            nonlocal received
            msg = await receive()
            if msg["type"] == "http.request":
                received += len(msg.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise _BodyTooLarge()
            return msg

        started = False

        async def send_with_headers(msg: dict[str, Any]) -> None:
            nonlocal started
            if msg["type"] == "http.response.start":
                started = True
                msg = dict(msg)
                msg["headers"] = list(msg.get("headers", [])) + SECURITY_HEADERS
            await send(msg)

        try:
            await asyncio.wait_for(self.app(scope, capped_receive, send_with_headers), timeout=REQUEST_TIMEOUT_S)
        except _BodyTooLarge:
            if not started:
                await _send_json(send, 413, {"error": "Request body too large (max 1 MB)."})
        except asyncio.TimeoutError:
            log.warning("request timed out: %s", path)
            if not started:
                await _send_json(send, 504, {"error": "Request timed out."})
        except Exception:  # noqa: BLE001 - never leak internals
            log.exception("unhandled error on %s", path)
            if not started:
                await _send_json(send, 500, {"error": "Internal error."})


class _BodyTooLarge(Exception):
    pass


def install_error_handlers(app: FastAPI) -> None:
    """Replace default error bodies with short generic messages."""

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in e.get("loc", [])[1:]) or "body" for e in exc.errors()})
        return JSONResponse({"error": "Invalid input.", "fields": fields}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else "Request failed."
        return JSONResponse({"error": detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _any(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse({"error": "Internal error."}, status_code=500)
