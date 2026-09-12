"""Sign-in with Google, and the session cookie that follows it.

The model
--------
A trainee signs in with their Google account. The browser gets an ID token from
Google, posts it here once, and this module asks Google whether that token is
real. If it is, the caller gets a signed session cookie carrying their email,
name and picture — nothing else. There is no password to store, reset or leak,
and no OAuth client secret in the deployment, because the ID-token flow needs
only a public client id.

Two deliberate omissions, both of which are the point rather than a shortcut:

**No model key is ever stored.** A trainee's Groq or OpenAI key stays in their
browser and rides on each request as a header, exactly as before sign-in
existed. Signing in identifies whose results and defects these are; it does not
give this server custody of anybody's credentials. A training instance that
collected forty API keys into a SQLite file on a free tier would be the most
dangerous thing in the project.

**The local sign-in is not available on a hosted instance.** Running on a laptop
with no Google client id configured, `/api/auth/local` issues a session so the
app is usable and testable offline. With `QTCAP_PUBLIC_MODE=1` that route is
refused outright — a development bypass that survives into production is how
authentication ends up decorative.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

import httpx

COOKIE_NAME = "qtcap_session"
SESSION_TTL_S = 12 * 3600
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class AuthError(Exception):
    """Sign-in failed. The message is safe to show the caller."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def google_client_id() -> str:
    return os.environ.get("QTCAP_GOOGLE_CLIENT_ID", "").strip()


def _secret() -> bytes:
    """Key for signing session cookies, in order of preference.

    1. QTCAP_SESSION_SECRET, if set. Explicit beats clever.
    2. A secret generated once and kept in the database. This is what stops a
       redeploy from signing a whole class out mid-session, and it only works
       because the database outlives the container — which is the same reason
       DATABASE_URL exists.
    3. A per-process random secret. Correct but forgetful: sessions die with the
       process. Better than a hard-coded default that ships in a public repo.
    """
    configured = os.environ.get("QTCAP_SESSION_SECRET", "").strip()
    if configured:
        return configured.encode()

    global _EPHEMERAL_SECRET
    if _EPHEMERAL_SECRET is not None:
        return _EPHEMERAL_SECRET

    try:
        from . import lab

        stored = lab.get_setting("session_secret")
        if not stored:
            stored = secrets.token_hex(32)
            lab.set_setting("session_secret", stored)
        _EPHEMERAL_SECRET = stored.encode()
    except Exception:  # noqa: BLE001 — no database is not a reason to fail sign-in
        _EPHEMERAL_SECRET = secrets.token_bytes(32)
    return _EPHEMERAL_SECRET


_EPHEMERAL_SECRET: bytes | None = None


def local_login_allowed() -> bool:
    """Offline sign-in is for a laptop, never for the shared class instance."""
    from .api.hosting import public_mode

    if public_mode():
        return False
    return not google_client_id() or os.environ.get(
        "QTCAP_ALLOW_LOCAL_LOGIN", "").strip().lower() in {"1", "true", "yes"}


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@dataclass
class User:
    email: str
    name: str = ""
    picture: str = ""
    provider: str = "google"
    issued_at: float = 0.0

    def public(self) -> dict[str, Any]:
        return {"email": self.email, "name": self.name, "picture": self.picture,
                "provider": self.provider}


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_session(user: User) -> str:
    payload = json.dumps({"email": user.email, "name": user.name, "picture": user.picture,
                          "provider": user.provider, "iat": time.time()},
                         separators=(",", ":")).encode()
    body = _b64(payload)
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def read_session(cookie: str | None) -> User | None:
    """Return the signed-in user, or None. Never raises on malformed input."""
    if not cookie or "." not in cookie:
        return None
    body, _, signature = cookie.partition(".")
    try:
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(signature), expected):
            return None
        data = json.loads(_unb64(body))
    except Exception:  # noqa: BLE001 — a bad cookie is an anonymous caller, not an error
        return None
    if time.time() - float(data.get("iat", 0)) > SESSION_TTL_S:
        return None
    email = str(data.get("email", "")).strip().lower()
    if not email or "@" not in email:
        return None
    return User(email=email, name=str(data.get("name", ""))[:80],
                picture=str(data.get("picture", ""))[:300],
                provider=str(data.get("provider", "google"))[:20],
                issued_at=float(data.get("iat", 0)))


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------
def verify_google_token(id_token: str) -> User:
    """Ask Google whether this ID token is real, and who it belongs to.

    Google's tokeninfo endpoint does the signature and expiry checking, so this
    deployment needs no key material and no crypto dependency. It costs one
    outbound call per sign-in, which is the right trade for a training app.
    """
    client_id = google_client_id()
    if not client_id:
        raise AuthError("Google sign-in is not configured on this instance.")
    token = (id_token or "").strip()
    if not token or len(token) > 4096 or token.count(".") != 2:
        raise AuthError("That does not look like a Google ID token.")

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(TOKENINFO_URL, params={"id_token": token})
    except httpx.HTTPError as exc:
        raise AuthError(f"Could not reach Google to verify the sign-in ({type(exc).__name__}).")
    if response.status_code != 200:
        raise AuthError("Google rejected that sign-in token.")

    claims = response.json()
    # Checking the audience is the whole point: a valid token issued for a
    # different application is still a valid token.
    if claims.get("aud") != client_id:
        raise AuthError("That token was issued for a different application.")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AuthError("Unexpected token issuer.")
    if str(claims.get("email_verified", "")).lower() not in {"true", "1"}:
        raise AuthError("That Google account has no verified email address.")
    try:
        if float(claims.get("exp", 0)) < time.time():
            raise AuthError("That sign-in token has expired. Try again.")
    except (TypeError, ValueError):
        raise AuthError("That sign-in token carries no expiry.")

    email = str(claims.get("email", "")).strip().lower()
    if not email:
        raise AuthError("Google returned no email address for that account.")
    allowed = allowed_domains()
    if allowed and email.rsplit("@", 1)[-1] not in allowed:
        raise AuthError(f"This instance is limited to {', '.join(sorted(allowed))} accounts.")
    return User(email=email, name=str(claims.get("name", ""))[:80],
                picture=str(claims.get("picture", ""))[:300], provider="google")


def allowed_domains() -> set[str]:
    """Optionally restrict sign-in to one or more email domains."""
    raw = os.environ.get("QTCAP_ALLOWED_EMAIL_DOMAINS", "")
    return {d.strip().lower().lstrip("@") for d in raw.split(",") if d.strip()}


def local_user(name: str) -> User:
    """A sign-in for offline work. Refused whenever the instance is public."""
    if not local_login_allowed():
        raise AuthError(
            "Local sign-in is disabled on this instance. Sign in with Google."
        )
    handle = "".join(ch for ch in (name or "trainee").lower() if ch.isalnum() or ch in "._-")[:40]
    handle = handle or "trainee"
    return User(email=f"{handle}@local", name=name[:80] or handle, provider="local")


def secret_is_durable() -> bool:
    """Will sessions survive a restart? Only if the secret does."""
    if os.environ.get("QTCAP_SESSION_SECRET", "").strip():
        return True
    try:
        from . import db, lab

        return db.backend() == "postgres" and bool(lab.get_setting("session_secret"))
    except Exception:  # noqa: BLE001
        return False


def auth_config() -> dict[str, Any]:
    """What the browser needs to render the right sign-in control."""
    return {
        "google_client_id": google_client_id(),
        "google_enabled": bool(google_client_id()),
        "local_enabled": local_login_allowed(),
        "allowed_domains": sorted(allowed_domains()),
        "session_hours": SESSION_TTL_S // 3600,
    }
