"""The storage layer, and the three dialect differences it hides.

`app/db.py` earns its tests not because it is complicated but because it is
silent: a placeholder that does not translate raises immediately and loudly,
while a `REAL` column that does not widen to `DOUBLE PRECISION` on Postgres
rounds every timestamp to the nearest few minutes and says nothing at all. The
second kind is what these tests are really for.
"""
from __future__ import annotations

import importlib
import os

import pytest

from app import db


@pytest.fixture
def sqlite_env(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("QTCAP_DATABASE_URL", raising=False)
    monkeypatch.setenv("QTCAP_DB_PATH", str(tmp_path / "lab.sqlite3"))
    db.reset_connection()
    yield
    db.reset_connection()


@pytest.fixture
def pg_env(monkeypatch):
    """Pretend Postgres is configured. No server is contacted."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.example.net:5432/qtcap")
    yield
    db.reset_connection()


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
def test_no_url_means_sqlite(sqlite_env):
    assert db.backend() == "sqlite"


def test_postgres_url_selects_postgres(pg_env):
    assert db.backend() == "postgres"


def test_postgres_scheme_alias_is_accepted(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert db.backend() == "postgres"


def test_unsupported_scheme_fails_loudly_rather_than_falling_back(monkeypatch):
    """A mysql:// URL must not silently write to a SQLite file instead."""
    monkeypatch.setenv("DATABASE_URL", "mysql://u:p@host/db")
    with pytest.raises(RuntimeError) as exc:
        db.backend()
    assert "postgres" in str(exc.value)


def test_qtcap_prefixed_url_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://a@one/db")
    monkeypatch.setenv("QTCAP_DATABASE_URL", "postgresql://b@two/db")
    assert "two" in db.database_url()


def test_whitespace_only_url_is_no_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert db.backend() == "sqlite"


# ---------------------------------------------------------------------------
# Placeholder translation
# ---------------------------------------------------------------------------
def test_sqlite_sql_is_passed_through_untouched(sqlite_env):
    sql = "SELECT * FROM results WHERE email = :email AND case_id = ?"
    assert db.translate(sql) == sql


def test_named_placeholders_become_psycopg_named(pg_env):
    out = db.translate("SELECT 1 FROM t WHERE email = :email AND id = :id")
    assert "%(email)s" in out and "%(id)s" in out
    assert ":email" not in out


def test_qmark_placeholders_become_percent_s(pg_env):
    out = db.translate("INSERT INTO t (a, b) VALUES (?, ?)")
    assert out.endswith("VALUES (%s, %s)")


def test_time_literals_are_not_mistaken_for_placeholders(pg_env):
    """`12:30` inside a string literal is data, not a bind parameter."""
    out = db.translate("SELECT * FROM t WHERE label = '12:30'")
    assert "12:30" in out
    assert "%(" not in out


def test_type_casts_are_left_alone(pg_env):
    out = db.translate("SELECT created::text FROM t")
    assert "::text" in out


# ---------------------------------------------------------------------------
# Schema translation
# ---------------------------------------------------------------------------
def test_real_widens_to_double_precision_on_postgres(pg_env):
    out = db.translate_schema("CREATE TABLE t (id TEXT, created REAL)")
    assert "DOUBLE PRECISION" in out
    assert " REAL" not in out


def test_real_is_left_alone_on_sqlite(sqlite_env):
    sql = "CREATE TABLE t (id TEXT, created REAL)"
    assert db.translate_schema(sql) == sql


def test_words_containing_real_are_not_rewritten(pg_env):
    out = db.translate_schema("CREATE TABLE t (real_name TEXT, unreal TEXT)")
    assert "real_name" in out and "unreal" in out
    assert "DOUBLE PRECISION" not in out


# ---------------------------------------------------------------------------
# describe() — what a health check may say, and what it may not
# ---------------------------------------------------------------------------
def test_describe_sqlite_is_marked_not_persistent(sqlite_env):
    info = db.describe()
    assert info["backend"] == "sqlite"
    assert info["persistent"] is False
    assert "DATABASE_URL" in info["note"]


def test_describe_postgres_never_leaks_the_password(pg_env):
    info = db.describe()
    assert info["backend"] == "postgres"
    assert info["persistent"] is True
    blob = repr(info)
    assert "p@" not in blob and "password" not in blob
    assert ":p@" not in blob
    assert "db.example.net" in info["location"]


# ---------------------------------------------------------------------------
# Round trip on the backend that needs no server
# ---------------------------------------------------------------------------
def test_location_is_never_empty_even_for_a_socket_url(monkeypatch):
    """A health check that reports an empty string tells nobody anything."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@/qtcap?host=/tmp&port=5433")
    assert db.describe()["location"]


def test_location_is_the_host_alone(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:secret@ep-x-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require",
    )
    assert db.safe_location() == "ep-x-123.ap-southeast-1.aws.neon.tech"


def test_round_trip_through_the_query_helpers(sqlite_env):
    db.script("CREATE TABLE IF NOT EXISTS probe (id TEXT PRIMARY KEY, created REAL)")
    db.run("INSERT INTO probe (id, created) VALUES (?, ?)", ("a", 1757000000.25))
    db.run_many([
        ("INSERT INTO probe (id, created) VALUES (?, ?)", ("b", 2.0)),
        ("INSERT INTO probe (id, created) VALUES (?, ?)", ("c", 3.0)),
    ])
    assert db.one("SELECT id FROM probe WHERE id = ?", ("a",))["id"] == "a"
    assert len(db.all_rows("SELECT id FROM probe")) == 3
    assert db.one("SELECT id FROM probe WHERE id = ?", ("zzz",)) is None


def test_timestamps_keep_sub_second_precision(sqlite_env):
    """The whole reason REAL is widened on Postgres, asserted here on SQLite."""
    db.script("CREATE TABLE IF NOT EXISTS stamps (id TEXT, created REAL)")
    exact = 1757000000.125
    db.run("INSERT INTO stamps (id, created) VALUES (?, ?)", ("x", exact))
    assert db.one("SELECT created FROM stamps WHERE id = ?", ("x",))["created"] == exact


def test_rows_are_plain_dicts_so_callers_cannot_tell_the_backend(sqlite_env):
    db.script("CREATE TABLE IF NOT EXISTS shape (id TEXT)")
    db.run("INSERT INTO shape (id) VALUES (?)", ("only",))
    row = db.one("SELECT id FROM shape")
    assert isinstance(row, dict) and row["id"] == "only"


def test_healthy_is_true_when_the_database_answers(sqlite_env):
    assert db.healthy() is True


def test_healthy_is_false_rather_than_raising_when_it_cannot_connect(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
    db.reset_connection()
    try:
        assert db.healthy() is False
    finally:
        db.reset_connection()


def test_reset_connection_is_safe_to_call_twice(sqlite_env):
    db.script("CREATE TABLE IF NOT EXISTS t2 (id TEXT)")
    db.reset_connection()
    db.reset_connection()
    db.run("INSERT INTO t2 (id) VALUES (?)", ("reopened",))
    assert db.one("SELECT id FROM t2")["id"] == "reopened"


def test_sqlite_path_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("QTCAP_DB_PATH", str(tmp_path / "elsewhere" / "lab.sqlite3"))
    assert db.sqlite_path().name == "lab.sqlite3"
    assert "elsewhere" in str(db.sqlite_path())


def test_the_data_directory_is_created_on_demand(tmp_path, monkeypatch):
    """A fresh clone has no data/ directory; the first write must not fail."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    target = tmp_path / "brand" / "new" / "lab.sqlite3"
    monkeypatch.setenv("QTCAP_DB_PATH", str(target))
    db.reset_connection()
    try:
        db.script("CREATE TABLE IF NOT EXISTS t3 (id TEXT)")
        assert target.exists()
    finally:
        db.reset_connection()
