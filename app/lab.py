"""The test lab's data: runs, per-case results, and defects.

Scope rules, which are the interesting part
-------------------------------------------
* **Results are private.** A trainee sees their own executions and nobody
  else's. Two people running the same case reach different rows.
* **Defects start private and are published deliberately.** A defect belongs to
  the person who raised it until they press Publish, at which point it appears
  on a board everyone can read. That mirrors how a real defect goes from a
  tester's notebook to a triage queue, and it gives the class one shared
  artefact at the end of the day.
* **Publishing is one-way per record but reversible by its author.** You can
  unpublish your own; you can never edit or unpublish somebody else's. Both are
  asserted in tests rather than promised here.

Storage goes through `app/db.py`, which is SQLite on a laptop and PostgreSQL
whenever `DATABASE_URL` is set. That switch is the difference between a training
instance people can come back to and one that forgets every account on each
redeploy — free hosting tiers cannot keep a file.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from . import db

_LOCK = threading.RLock()

SEVERITIES = ("critical", "high", "medium", "low")
VERDICTS = ("pass", "fail", "blocked", "not_run")
SUITES = ("rag", "agent", "multi")


def db_path() -> Path:
    """Where SQLite would write. Meaningless when DATABASE_URL points elsewhere."""
    return db.sqlite_path()


_READY = False


def ensure_schema() -> None:
    """Create the tables once per process. Safe to call from anywhere."""
    global _READY
    if _READY:
        return
    with _LOCK:
        if _READY:
            return
        db.script(SCHEMA)
        _READY = True


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
  email TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  passcode_hash TEXT NOT NULL,   -- PBKDF2-SHA256, never the passcode itself
  salt TEXT NOT NULL,
  iterations INTEGER NOT NULL,
  created_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  failed_attempts INTEGER NOT NULL DEFAULT 0,
  locked_until REAL
);

CREATE TABLE IF NOT EXISTS results (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  case_id TEXT NOT NULL,
  suite TEXT NOT NULL,
  area TEXT NOT NULL,
  executor TEXT NOT NULL,
  capability TEXT NOT NULL,
  status TEXT NOT NULL,            -- Pass | Fail | Fail (expected) | Blocked
  verdict TEXT,                    -- the tester's own call, if they made one
  actual TEXT NOT NULL,
  evidence TEXT NOT NULL,
  remark TEXT NOT NULL,
  duration_ms REAL NOT NULL,
  run_id TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_email ON results(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_results_case ON results(email, case_id);

CREATE TABLE IF NOT EXISTS defects (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  reporter_name TEXT NOT NULL,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  suite TEXT NOT NULL,
  case_id TEXT,
  steps TEXT NOT NULL,
  expected TEXT NOT NULL,
  actual TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  published INTEGER NOT NULL DEFAULT 0,
  published_at REAL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_defects_email ON defects(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_defects_public ON defects(published, published_at DESC);
"""


def reset() -> None:
    """Test hook: drop everything and start again."""
    global _READY
    with _LOCK:
        db.script("DROP TABLE IF EXISTS results; DROP TABLE IF EXISTS defects; "
                  "DROP TABLE IF EXISTS accounts; DROP TABLE IF EXISTS settings;")
        _READY = False
        ensure_schema()


# ---------------------------------------------------------------------------
# Instance settings
# ---------------------------------------------------------------------------
def get_setting(key: str) -> str | None:
    ensure_schema()
    row = db.one("SELECT value FROM settings WHERE key = :key", {"key": key})
    return row["value"] if row else None


def set_setting(key: str, value: str) -> None:
    ensure_schema()
    with _LOCK:
        if db.one("SELECT 1 AS x FROM settings WHERE key = :key", {"key": key}):
            db.run("UPDATE settings SET value = :value WHERE key = :key",
                   {"key": key, "value": value})
        else:
            db.run("INSERT INTO settings (key, value) VALUES (:key, :value)",
                   {"key": key, "value": value})


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
# A trainee needs an identity so their results and defects are theirs. Google
# gives that identity for free when an instance is configured for it, but an
# instance that has not been configured must not be unusable — so this is the
# built-in alternative: an email address and a passcode the trainee chooses.
#
# What this is and is not: the passcode is hashed with PBKDF2-SHA256 and a
# per-account salt, never stored or logged in the clear, and repeated wrong
# guesses lock an account for a few minutes. The email address is **not
# verified**, because verifying it needs a mail service this project does not
# have and should not grow for a classroom tool. So this is a real account with
# a real secret, protecting a real boundary between trainees — and it is not
# proof of who someone is. Where that distinction matters, configure Google.
PBKDF2_ITERATIONS = 240_000
MIN_PASSCODE = 8
MAX_FAILED = 6
LOCKOUT_S = 300


class AccountError(Exception):
    """Sign-up or sign-in failed. The message is safe to show the caller."""


def _hash_passcode(passcode: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> str:
    import hashlib

    return hashlib.pbkdf2_hmac("sha256", passcode.encode(), salt, iterations).hex()


def _clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1] or len(email) > 160:
        raise AccountError("That does not look like an email address.")
    return email


def create_account(email: str, name: str, passcode: str) -> dict[str, Any]:
    import secrets as _secrets

    email = _clean_email(email)
    if len(passcode or "") < MIN_PASSCODE:
        raise AccountError(f"Choose a passcode of at least {MIN_PASSCODE} characters.")
    salt = _secrets.token_bytes(16)
    now = time.time()
    row = {"email": email, "name": (name or email.split("@")[0])[:80],
           "passcode_hash": _hash_passcode(passcode, salt), "salt": salt.hex(),
           "iterations": PBKDF2_ITERATIONS, "created_at": now, "last_seen_at": now,
           "failed_attempts": 0, "locked_until": None}
    ensure_schema()
    with _LOCK:
        if db.one("SELECT 1 AS x FROM accounts WHERE email = :email", {"email": email}):
            raise AccountError("An account already exists for that address. Sign in instead.")
        db.run(
            "INSERT INTO accounts (email,name,passcode_hash,salt,iterations,created_at,"
            "last_seen_at,failed_attempts,locked_until) VALUES (:email,:name,:passcode_hash,"
            ":salt,:iterations,:created_at,:last_seen_at,:failed_attempts,:locked_until)", row)
    return {"email": email, "name": row["name"]}


def verify_account(email: str, passcode: str) -> dict[str, Any]:
    """Check a passcode. Wrong answers are slow to matter and quick to lock."""
    import hmac as _hmac

    email = _clean_email(email)
    ensure_schema()
    with _LOCK:
        row = db.one("SELECT * FROM accounts WHERE email = :email", {"email": email})
        if row is None:
            # Same message either way: which addresses have accounts is not
            # something an unauthenticated caller gets to enumerate.
            raise AccountError("No account with that address and passcode.")
        if row["locked_until"] and row["locked_until"] > time.time():
            wait = int(row["locked_until"] - time.time())
            raise AccountError(f"Too many attempts. Try again in {wait} seconds.")

        candidate = _hash_passcode(passcode or "", bytes.fromhex(row["salt"]), row["iterations"])
        if not _hmac.compare_digest(candidate, row["passcode_hash"]):
            failed = (row["failed_attempts"] or 0) + 1
            locked = time.time() + LOCKOUT_S if failed >= MAX_FAILED else None
            db.run("UPDATE accounts SET failed_attempts = :failed, locked_until = :locked "
                   "WHERE email = :email",
                   {"failed": failed, "locked": locked, "email": email})
            raise AccountError("No account with that address and passcode.")

        db.run("UPDATE accounts SET failed_attempts = 0, locked_until = NULL, "
               "last_seen_at = :now WHERE email = :email", {"now": time.time(), "email": email})
        return {"email": email, "name": row["name"]}


def account_exists(email: str) -> bool:
    try:
        email = _clean_email(email)
    except AccountError:
        return False
    ensure_schema()
    return db.one("SELECT 1 AS x FROM accounts WHERE email = :email",
                  {"email": email}) is not None


def account_count() -> int:
    ensure_schema()
    return int(db.one("SELECT COUNT(*) AS n FROM accounts")["n"])


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
def record_result(email: str, case: dict[str, Any], outcome: Any, duration_ms: float,
                  run_id: str) -> dict[str, Any]:
    row = {
        "id": uuid.uuid4().hex[:16],
        "email": email,
        "case_id": case["id"],
        "suite": case.get("suite", "agent"),
        "area": case.get("area", ""),
        "executor": case.get("executor", ""),
        "capability": case.get("capability", ""),
        "status": outcome.status if outcome.status != "Fail"
        else ("Fail (expected)" if case.get("capability") == "absent" else "Fail"),
        "verdict": None,
        "actual": (outcome.actual or "")[:4000],
        "evidence": json.dumps(outcome.evidence, default=str)[:4000],
        "remark": (outcome.remark or "")[:2000],
        "duration_ms": round(duration_ms, 1),
        "run_id": run_id,
        "created_at": time.time(),
    }
    ensure_schema()
    db.run(
        "INSERT INTO results (id,email,case_id,suite,area,executor,capability,status,verdict,"
        "actual,evidence,remark,duration_ms,run_id,created_at) VALUES "
        "(:id,:email,:case_id,:suite,:area,:executor,:capability,:status,:verdict,:actual,"
        ":evidence,:remark,:duration_ms,:run_id,:created_at)", row)
    return row


def latest_results(email: str, suite: str | None = None) -> dict[str, dict[str, Any]]:
    """The most recent result per case for this user — what a dashboard shows."""
    ensure_schema()
    sql = ("SELECT * FROM results WHERE email = :email " +
           ("AND suite = :suite " if suite else "") + "ORDER BY created_at ASC")
    params = {"email": email}
    if suite:
        params["suite"] = suite
    latest: dict[str, dict[str, Any]] = {}
    for row in db.all_rows(sql, params):
        latest[row["case_id"]] = row            # later rows overwrite earlier ones
    return latest


def set_verdict(email: str, case_id: str, verdict: str) -> dict[str, Any] | None:
    """The tester's own call, which may disagree with the harness — and should be
    allowed to. An automated check is evidence, not a verdict."""
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    ensure_schema()
    with _LOCK:
        row = db.one("SELECT id FROM results WHERE email = :email AND case_id = :case_id "
                     "ORDER BY created_at DESC LIMIT 1", {"email": email, "case_id": case_id})
        if row is None:
            return None
        db.run("UPDATE results SET verdict = :verdict WHERE id = :id",
               {"verdict": verdict, "id": row["id"]})
        return db.one("SELECT * FROM results WHERE id = :id", {"id": row["id"]})


def summary(email: str) -> dict[str, Any]:
    """Everything the summary report needs, per suite and overall."""
    latest = latest_results(email)
    by_suite: dict[str, dict[str, int]] = {s: {"total": 0, "Pass": 0, "Fail": 0,
                                               "Fail (expected)": 0, "Blocked": 0,
                                               "verdicts": 0} for s in SUITES}
    for row in latest.values():
        bucket = by_suite.setdefault(row["suite"], {"total": 0, "Pass": 0, "Fail": 0,
                                                    "Fail (expected)": 0, "Blocked": 0,
                                                    "verdicts": 0})
        bucket["total"] += 1
        bucket[row["status"]] = bucket.get(row["status"], 0) + 1
        if row["verdict"]:
            bucket["verdicts"] += 1

    defects = my_defects(email)
    return {
        "executed": len(latest),
        "by_suite": by_suite,
        "totals": {
            "Pass": sum(b["Pass"] for b in by_suite.values()),
            "Fail": sum(b["Fail"] for b in by_suite.values()),
            "Fail (expected)": sum(b["Fail (expected)"] for b in by_suite.values()),
            "Blocked": sum(b["Blocked"] for b in by_suite.values()),
        },
        "defects": {
            "total": len(defects),
            "published": sum(1 for d in defects if d["published"]),
            "by_severity": {s: sum(1 for d in defects if d["severity"] == s) for s in SEVERITIES},
        },
        "last_run_at": max((r["created_at"] for r in latest.values()), default=None),
    }


# ---------------------------------------------------------------------------
# Defects
# ---------------------------------------------------------------------------
def raise_defect(email: str, reporter_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    title = (payload.get("title") or "").strip()
    if not title:
        raise ValueError("A defect needs a title.")
    severity = (payload.get("severity") or "medium").lower()
    if severity not in SEVERITIES:
        severity = "medium"
    suite = (payload.get("suite") or "rag").lower()
    if suite not in SUITES:
        suite = "rag"
    now = time.time()
    row = {
        "id": f"QT-{uuid.uuid4().hex[:6].upper()}",
        "email": email,
        "reporter_name": (reporter_name or email.split("@")[0])[:80],
        "title": title[:200],
        "severity": severity,
        "suite": suite,
        "case_id": (payload.get("case_id") or "")[:40] or None,
        "steps": (payload.get("steps") or "")[:4000],
        "expected": (payload.get("expected") or "")[:2000],
        "actual": (payload.get("actual") or "")[:4000],
        "status": "open",
        "published": 0,
        "published_at": None,
        "created_at": now,
        "updated_at": now,
    }
    ensure_schema()
    db.run(
        "INSERT INTO defects (id,email,reporter_name,title,severity,suite,case_id,steps,"
        "expected,actual,status,published,published_at,created_at,updated_at) VALUES "
        "(:id,:email,:reporter_name,:title,:severity,:suite,:case_id,:steps,:expected,:actual,"
        ":status,:published,:published_at,:created_at,:updated_at)", row)
    return _redact(row)


def my_defects(email: str) -> list[dict[str, Any]]:
    ensure_schema()
    return [_redact(r) for r in db.all_rows(
        "SELECT * FROM defects WHERE email = :email ORDER BY created_at DESC", {"email": email})]


def public_defects(limit: int = 200) -> list[dict[str, Any]]:
    """The shared board. Readable by anyone, signed in or not."""
    ensure_schema()
    return [_redact(r, public=True) for r in db.all_rows(
        "SELECT * FROM defects WHERE published = 1 ORDER BY published_at DESC LIMIT :limit",
        {"limit": max(1, min(limit, 500))})]


def set_published(email: str, defect_id: str, published: bool) -> dict[str, Any] | None:
    """Publish or withdraw. Only the author of a defect can move it."""
    ensure_schema()
    with _LOCK:
        row = db.one("SELECT * FROM defects WHERE id = :id", {"id": defect_id})
        if row is None or row["email"] != email:
            return None                      # not yours: indistinguishable from not existing
        db.run("UPDATE defects SET published = :published, published_at = :published_at, "
               "updated_at = :updated_at WHERE id = :id",
               {"published": 1 if published else 0,
                "published_at": time.time() if published else None,
                "updated_at": time.time(), "id": defect_id})
        return _redact(db.one("SELECT * FROM defects WHERE id = :id", {"id": defect_id}))


def update_defect(email: str, defect_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"title", "severity", "steps", "expected", "actual", "status"}
    fields = {k: v for k, v in changes.items() if k in allowed and v is not None}
    if not fields:
        return None
    if "severity" in fields and fields["severity"] not in SEVERITIES:
        fields.pop("severity")
    if "status" in fields and fields["status"] not in {"open", "triaged", "fixed", "rejected"}:
        fields.pop("status")
    ensure_schema()
    with _LOCK:
        row = db.one("SELECT email FROM defects WHERE id = :id", {"id": defect_id})
        if row is None or row["email"] != email:
            return None
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        fields.update({"id": defect_id, "updated_at": time.time()})
        db.run(f"UPDATE defects SET {sets}, updated_at = :updated_at WHERE id = :id", fields)
        return _redact(db.one("SELECT * FROM defects WHERE id = :id", {"id": defect_id}))


def delete_defect(email: str, defect_id: str) -> bool:
    ensure_schema()
    with _LOCK:
        row = db.one("SELECT email FROM defects WHERE id = :id", {"id": defect_id})
        if row is None or row["email"] != email:
            return False
        db.run("DELETE FROM defects WHERE id = :id", {"id": defect_id})
        return True


def _redact(row: dict[str, Any], public: bool = False) -> dict[str, Any]:
    """Never hand a full email address to the public board.

    A defect board is a shared artefact; a list of forty verified email
    addresses is a mailing list. The author's display name and a masked handle
    are enough to know whose finding it is.
    """
    from .llm.session import redact as redact_secrets

    out = dict(row)
    out["published"] = bool(row.get("published"))
    for field in ("steps", "expected", "actual", "title"):
        if out.get(field):
            out[field] = redact_secrets(str(out[field]))
    if public:
        out.pop("email", None)
        out["reporter"] = out.get("reporter_name") or "anonymous"
    else:
        out["reporter"] = out.get("reporter_name") or out.get("email", "")
    return out


def export_markdown(email: str, name: str) -> str:
    """The artefact worth keeping when the container goes away."""
    data = summary(email)
    latest = latest_results(email)
    lines = [f"# Test report — {name or email}", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M', time.localtime())}.", "",
             "## Execution", "",
             "| Suite | Executed | Pass | Fail | Capability gap | Blocked |",
             "|---|---|---|---|---|---|"]
    for suite, bucket in data["by_suite"].items():
        lines.append(f"| {suite} | {bucket['total']} | {bucket['Pass']} | {bucket['Fail']} | "
                     f"{bucket['Fail (expected)']} | {bucket['Blocked']} |")
    lines += ["", "## Defects raised", ""]
    defects = my_defects(email)
    if not defects:
        lines.append("_None._")
    for defect in defects:
        lines += [f"### {defect['id']} — {defect['title']}", "",
                  f"- Severity: **{defect['severity']}** · Suite: {defect['suite']} · "
                  f"Status: {defect['status']} · "
                  f"{'published' if defect['published'] else 'private'}"]
        if defect.get("case_id"):
            lines.append(f"- Test case: `{defect['case_id']}`")
        if defect.get("steps"):
            lines += ["", "**Steps**", "", defect["steps"]]
        if defect.get("expected"):
            lines += ["", "**Expected**", "", defect["expected"]]
        if defect.get("actual"):
            lines += ["", "**Actual**", "", defect["actual"]]
        lines.append("")
    failures = [r for r in latest.values() if r["status"] == "Fail"]
    if failures:
        lines += ["## Failing cases with no defect raised", ""]
        raised = {d.get("case_id") for d in defects}
        orphans = [r for r in failures if r["case_id"] not in raised]
        if not orphans:
            lines.append("_Every failure has a defect against it._")
        for row in orphans[:40]:
            lines.append(f"- `{row['case_id']}` ({row['area']}) — {row['remark'][:160]}")
    return "\n".join(lines) + "\n"
