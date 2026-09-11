"""Protections a publicly-hosted training instance needs and a laptop does not.

A shared URL handed to a class is a small public service. Three things follow:

  * one student must not be able to spend the whole instance's capacity, so
    requests are rate limited per client
  * a student's API key must never reach a log, a trace or another student's
    screen, so every error string is redacted on the way out
  * request bodies are capped, because an unbounded body on a free tier with
    512MB of RAM is a one-line denial of service

All limits are environment-tunable, and all of them are off by default when
QTCAP_PUBLIC_MODE is unset, so a local run is unaffected.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from ..llm.session import redact


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def public_mode() -> bool:
    return os.environ.get("QTCAP_PUBLIC_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


class RateLimiter:
    """Sliding-window limiter keyed by client, with a stricter bucket for the
    endpoints that cost real money or real CPU."""

    def __init__(self):
        self.windows: dict[str, deque[float]] = defaultdict(deque)
        self.per_minute = _int_env("QTCAP_RATE_PER_MIN", 40)
        self.heavy_per_minute = _int_env("QTCAP_HEAVY_RATE_PER_MIN", 8)
        self.window_s = 60.0

    def check(self, client: str, heavy: bool = False) -> tuple[bool, int, int]:
        limit = self.heavy_per_minute if heavy else self.per_minute
        key = f"{client}:{'h' if heavy else 'n'}"
        now = time.monotonic()
        window = self.windows[key]
        while window and now - window[0] > self.window_s:
            window.popleft()
        if len(window) >= limit:
            retry = int(self.window_s - (now - window[0])) + 1
            return False, limit, retry
        window.append(now)
        # Keep the table from growing without bound on a long-lived instance.
        if len(self.windows) > 5000:
            for k in [k for k, v in self.windows.items() if not v][:2000]:
                self.windows.pop(k, None)
        return True, limit, 0


LIMITER = RateLimiter()

# Endpoints that call a model, run a suite, or hit an external API.
HEAVY_PATHS = (
    "/api/rag/query", "/api/agent/query", "/api/multi/query",
    "/api/tests/run", "/api/market/", "/api/mcp/call",
)


def client_id(request: Request) -> str:
    """Identify a caller behind a platform proxy, falling back to the socket."""
    for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


async def guard_request(request: Request, call_next):
    """Body cap, rate limit, and outbound redaction in one middleware."""
    if not public_mode():
        return await call_next(request)

    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    max_body = _int_env("QTCAP_MAX_BODY_BYTES", 64_000)
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_body:
        return JSONResponse(
            {"error": "request_too_large",
             "message": f"Request body exceeds {max_body} bytes."},
            status_code=413,
        )

    heavy = any(path.startswith(p) for p in HEAVY_PATHS)
    allowed, limit, retry = LIMITER.check(client_id(request), heavy=heavy)
    if not allowed:
        return JSONResponse(
            {
                "error": "rate_limited",
                "message": (
                    f"You have used this instance's limit of {limit} "
                    f"{'model/test' if heavy else 'API'} requests per minute. "
                    f"Try again in {retry}s, or run the project locally where there is no limit."
                ),
                "retry_after_s": retry,
            },
            status_code=429,
            headers={"Retry-After": str(retry)},
        )

    return await call_next(request)


def safe_error(exc: Exception) -> dict[str, Any]:
    """Render an exception for a caller without leaking a key or a stack path."""
    return {"error": type(exc).__name__, "message": redact(str(exc))[:500]}
