"""One storage layer, two backends: SQLite on a laptop, PostgreSQL when hosted.

Why this file exists
--------------------
The test lab's accounts, results and defects were in a SQLite file, which is
exactly right on a laptop and exactly wrong on a free hosting tier: free
instances cannot attach a persistent disk, so a redeploy or a spin-down deletes
the file and everyone's accounts with it. Telling a class to re-register after
every deploy is not a workaround, it is a broken product.

So: set `DATABASE_URL` to a Postgres connection string and the same code writes
there instead. Unset, nothing changes and no database server is needed.

Keeping two dialects honest
---------------------------
Three differences matter, and each is handled in one place rather than sprinkled
through the queries:

* **Placeholders.** SQLite takes `?` and `:name`; psycopg takes `%s` and
  `%(name)s`. Every query in this project is written in SQLite's style and
  translated on the way out.
* **Types.** SQLite's `REAL` is a 64-bit float; Postgres's `REAL` is 32-bit,
  which silently rounds a Unix timestamp to the nearest few minutes — the kind
  of defect that shows up as "why are these events all at the same time?" a
  month later. The schema declares `REAL` and it becomes `DOUBLE PRECISION` on
  Postgres.
* **Rows.** Both backends return mappings here, so calling code never learns
  which one it is talking to.

What is deliberately not here: an ORM, migrations, and a connection pool. Four
tables and a handful of queries do not need them, and every dependency added to
a training project is one more thing a trainee has to understand before they can
read the part that matters.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from .config import ROOT

_LOCK = threading.RLock()
_STATE: dict[str, Any] = {}

_NAMED = re.compile(r"(?<![:\w]):([a-zA-Z_]\w*)")


def database_url() -> str:
    """Postgres connection string, or empty for SQLite.

    Render, Neon, Supabase and Heroku all expose it as DATABASE_URL, so that is
    the name to honour; QTCAP_DATABASE_URL wins when both are set.
    """
    return (os.environ.get("QTCAP_DATABASE_URL")
            or os.environ.get("DATABASE_URL") or "").strip()


def backend() -> str:
    url = database_url()
    if url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    if url:
        raise RuntimeError(
            f"DATABASE_URL must be a postgres:// or postgresql:// URL, not {url.split(':')[0]}://"
        )
    return "sqlite"


def sqlite_path() -> Path:
    return Path(os.environ.get("QTCAP_DB_PATH", str(ROOT / "data" / "lab.sqlite3")))


def describe() -> dict[str, Any]:
    """What a health check should say about storage — never the credentials."""
    kind = backend()
    if kind == "sqlite":
        return {"backend": "sqlite", "location": str(sqlite_path()),
                "persistent": False,
                "note": "A free hosting tier wipes this file on redeploy. Set DATABASE_URL "
                        "to a Postgres database to keep accounts and results."}
    return {"backend": "postgres", "location": safe_location(), "persistent": True}


def safe_location() -> str:
    """The host, for a health check. Never the user, password or database name."""
    url = database_url()
    after_scheme = url.split("://", 1)[-1]
    authority = after_scheme.split("/", 1)[0].split("?", 1)[0]
    host = authority.rsplit("@", 1)[-1]
    return host or "configured"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def _connect():
    kind = backend()
    if kind == "sqlite":
        path = sqlite_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL keeps a reader from blocking on the writer, which matters the
        # moment a class of forty presses Run at the same time.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    import psycopg
    from psycopg.rows import dict_row

    url = database_url()
    # Managed Postgres almost always requires TLS, and the common copy-paste
    # mistake is a URL without it.
    if "sslmode=" not in url and not url.startswith("postgresql://localhost"):
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg.connect(url, row_factory=dict_row, autocommit=True)


def connection():
    """The shared connection, opened on first use and reconnected if dropped."""
    with _LOCK:
        conn = _STATE.get("conn")
        if conn is not None and not _closed(conn):
            return conn
        _STATE["conn"] = _connect()
        return _STATE["conn"]


def _closed(conn) -> bool:
    try:
        return bool(getattr(conn, "closed", False))
    except Exception:  # noqa: BLE001
        return True


def reset_connection() -> None:
    """Drop the cached connection. Used by tests and after a backend switch."""
    with _LOCK:
        conn = _STATE.pop("conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


# ---------------------------------------------------------------------------
# Dialect
# ---------------------------------------------------------------------------
def translate(sql: str) -> str:
    """Rewrite SQLite-style SQL for whichever backend is configured."""
    if backend() == "sqlite":
        return sql
    sql = _NAMED.sub(lambda m: f"%({m.group(1)})s", sql)
    sql = sql.replace("?", "%s")
    return sql


def translate_schema(sql: str) -> str:
    """Schema DDL needs type names as well as placeholders."""
    if backend() == "sqlite":
        return sql
    # REAL is 32-bit in Postgres and would round Unix timestamps to minutes.
    sql = re.sub(r"\bREAL\b", "DOUBLE PRECISION", sql)
    return sql


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
def run(sql: str, params: Any = None) -> None:
    """Execute a statement that returns nothing."""
    with _LOCK:
        conn = connection()
        cur = conn.cursor()
        cur.execute(translate(sql), params or ())
        if backend() == "sqlite":
            conn.commit()
        cur.close()


def run_many(statements: Iterable[tuple[str, Any]]) -> None:
    """Several statements as one unit of work."""
    with _LOCK:
        conn = connection()
        cur = conn.cursor()
        for sql, params in statements:
            cur.execute(translate(sql), params or ())
        if backend() == "sqlite":
            conn.commit()
        cur.close()


def one(sql: str, params: Any = None) -> dict[str, Any] | None:
    with _LOCK:
        cur = connection().cursor()
        cur.execute(translate(sql), params or ())
        row = cur.fetchone()
        cur.close()
        return dict(row) if row is not None else None


def all_rows(sql: str, params: Any = None) -> list[dict[str, Any]]:
    with _LOCK:
        cur = connection().cursor()
        cur.execute(translate(sql), params or ())
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def script(sql: str) -> None:
    """Run schema DDL. Split by statement, because psycopg takes one at a time."""
    with _LOCK:
        conn = connection()
        cur = conn.cursor()
        for statement in [s.strip() for s in translate_schema(sql).split(";") if s.strip()]:
            cur.execute(statement)
        if backend() == "sqlite":
            conn.commit()
        cur.close()


def healthy() -> bool:
    """Can this instance actually reach its database right now?"""
    try:
        one("SELECT 1 AS ok")
        return True
    except Exception:  # noqa: BLE001
        return False
