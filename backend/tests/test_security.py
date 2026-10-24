"""Lane B task 4: HTTP hardening (rate limit, size cap, headers, generic errors, timeout)."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import security
from app.api.security import HardeningMiddleware, RateLimiter, install_error_handlers
from app.main import app


def test_security_headers_on_every_response() -> None:
    r = TestClient(app, client=("10.0.1.1", 1)).get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["x-frame-options"] == "DENY"


def test_rate_limit_60_per_minute_per_ip() -> None:
    a = TestClient(app, client=("10.0.1.2", 1))
    codes = [a.get("/api/meta/sources").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429
    # A different IP is unaffected.
    assert TestClient(app, client=("10.0.1.3", 1)).get("/api/meta/sources").status_code == 200


def test_rate_limiter_window_expires() -> None:
    rl = RateLimiter(limit=2, window_s=60)
    assert rl.allow("ip", now=0) and rl.allow("ip", now=1)
    assert not rl.allow("ip", now=2)
    assert rl.allow("ip", now=61)


def test_body_over_1mb_rejected() -> None:
    c = TestClient(app, client=("10.0.1.4", 1))
    r = c.post("/api/trip/plan", content=b"x" * 1_000_001, headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert r.json() == {"error": "Request body too large (max 1 MB)."}


def test_generic_errors_without_stack_traces() -> None:
    mini = FastAPI()
    install_error_handlers(mini)

    @mini.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail")

    r = TestClient(HardeningMiddleware(mini), raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert "secret" not in r.text and "Traceback" not in r.text


def test_request_timeout(monkeypatch) -> None:
    monkeypatch.setattr(security, "REQUEST_TIMEOUT_S", 0.05)
    mini = FastAPI()

    @mini.get("/slow")
    async def slow() -> dict:
        await asyncio.sleep(1)
        return {}

    r = TestClient(HardeningMiddleware(mini)).get("/slow")
    assert r.status_code == 504
    assert r.json() == {"error": "Request timed out."}


def test_spoofed_forwarded_for_only_uses_last_hop(monkeypatch) -> None:
    monkeypatch.setenv("FATHOM_TRUST_PROXY", "true")
    scope = {"headers": [(b"x-forwarded-for", b"1.1.1.1, 9.9.9.9")], "client": ("10.0.0.9", 1)}
    assert security._client_ip(scope) == "9.9.9.9"
    monkeypatch.setenv("FATHOM_TRUST_PROXY", "false")
    assert security._client_ip(scope) == "10.0.0.9"
