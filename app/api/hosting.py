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
from fastapi.responses import JSONResponse, RedirectResponse

from ..llm.session import redact


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def public_mode() -> bool:
    return os.environ.get("QTCAP_PUBLIC_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Custom domain
# ---------------------------------------------------------------------------
# Serving the class from your own subdomain — capstone.qualitythought.in rather
# than <service>.onrender.com — is DNS plus one CNAME, and needs no code at all.
# What *does* need code is the tidy-up afterwards:
#
#   * the platform hostname keeps working forever, so the same app answers on
#     two URLs. Students bookmark whichever one they were sent, screenshots in
#     bug reports disagree, and a finding filed against one is hard to reproduce
#     on the other. QTCAP_CANONICAL_HOST redirects every other hostname to the
#     one you handed out.
#   * a hostname nobody configured should not be served at all. Anyone can point
#     a DNS record of their own at a hosting platform; without a host check your
#     app answers under their name. QTCAP_ALLOWED_HOSTS closes that.
#
# Both are opt-in. Unset, nothing changes — which is what a laptop wants.

def _host_of(value: str) -> str:
    """Normalise a configured or received host: no scheme, no port, lowercase."""
    host = (value or "").strip().lower()
    if "//" in host:
        host = host.split("//", 1)[1]
    host = host.split("/", 1)[0].strip()
    # Strip a port, but leave a bracketed IPv6 literal intact.
    if host.startswith("["):
        return host
    return host.split(":", 1)[0]


def canonical_host() -> str:
    """The one hostname this instance should be reached by, or '' for none."""
    return _host_of(os.environ.get("QTCAP_CANONICAL_HOST", ""))


def allowed_hosts() -> set[str]:
    """Hostnames this instance will answer to.

    Empty means "answer to anything", which is the local default. When a
    canonical host is set it is always allowed, as are the loopback names a
    health check and the UI tests use.
    """
    configured = {
        _host_of(part)
        for part in os.environ.get("QTCAP_ALLOWED_HOSTS", "").split(",")
        if _host_of(part)
    }
    if not configured:
        return set()
    canonical = canonical_host()
    if canonical:
        configured.add(canonical)
    configured.update({"localhost", "127.0.0.1", "testserver", "[::1]"})
    return configured


def host_allowed(host: str) -> bool:
    allowed = allowed_hosts()
    if not allowed:
        return True
    received = _host_of(host)
    if received in allowed:
        return True
    # A leading dot in configuration means "this domain and any subdomain",
    # so one entry covers preview deployments under the same zone.
    return any(
        entry.startswith(".") and (received == entry[1:] or received.endswith(entry))
        for entry in allowed
    )


def canonical_redirect(request: Request) -> RedirectResponse | None:
    """Send a GET/HEAD arriving on any other hostname to the canonical one.

    Only safe methods are redirected. Bouncing a POST across hostnames loses the
    per-request model key the console sends in a header, and the student sees a
    puzzling failure rather than a redirect — so a write on the wrong hostname
    is served where it landed.
    """
    canonical = canonical_host()
    if not canonical or request.method not in {"GET", "HEAD"}:
        return None
    received = _host_of(request.headers.get("host", ""))
    if not received or received == canonical:
        return None
    # Never redirect the health check: the platform probes the service by its
    # own hostname, and a 308 there reads as an unhealthy deploy.
    if request.url.path == "/api/health":
        return None
    target = request.url.replace(netloc=canonical, scheme="https")
    return RedirectResponse(str(target), status_code=308)


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
    """Host policy, body cap, rate limit and outbound redaction in one middleware."""
    if not public_mode():
        return await call_next(request)

    # Host policy runs on every path, not just the API: the console itself is
    # what a stray hostname would otherwise serve.
    if not host_allowed(request.headers.get("host", "")):
        return JSONResponse(
            {"error": "unknown_host",
             "message": "This hostname is not configured for this instance."},
            status_code=421,
        )
    redirect = canonical_redirect(request)
    if redirect is not None:
        return redirect

    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)

    # One endpoint legitimately carries a document rather than a question, so it
    # gets its own cap. Everything else stays on the small one — an unbounded
    # body on a 512MB free tier is a one-line denial of service.
    if path == "/api/rag/documents" and request.method == "POST":
        max_body = _int_env("QTCAP_MAX_UPLOAD_BYTES", 320_000)
    else:
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
