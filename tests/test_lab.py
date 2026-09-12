"""Tests for the multi-user test lab: sign-in, per-user results, defect publishing.

The defects worth catching here are the ones that only exist once an
application has more than one user:

  * can one trainee read, alter or delete another's work
  * does a development sign-in survive into a hosted deployment
  * does a model key ever reach the server's storage
  * does a private defect stay private until its author publishes it

Run:
    pytest tests/test_lab.py -v
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, db, lab  # noqa: E402


# The whole suite runs twice when QTCAP_TEST_POSTGRES points at a database:
# once on SQLite and once on Postgres. Two backends that are never both tested
# is one backend and a liability.
POSTGRES_URL = os.environ.get("QTCAP_TEST_POSTGRES", "")


@pytest.fixture(autouse=True, params=["sqlite", "postgres"])
def backend(request, monkeypatch):
    if request.param == "postgres":
        if not POSTGRES_URL:
            pytest.skip("set QTCAP_TEST_POSTGRES to run this suite against Postgres too")
        monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    return request.param


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch, backend):
    monkeypatch.setenv("QTCAP_DB_PATH", str(tmp_path / "lab.sqlite3"))
    if backend == "sqlite":
        monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("QTCAP_DATABASE_URL", raising=False)
    db.reset_connection()
    lab._READY = False
    lab.reset()
    yield
    db.reset_connection()
    lab._READY = False


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("QTCAP_PUBLIC_MODE", raising=False)
    from app.api.main import app

    return TestClient(app)


def sign_in(client: TestClient, name: str) -> TestClient:
    """A separate client per trainee, so their cookie jars stay separate."""
    response = client.post("/api/auth/local", json={"name": name})
    assert response.status_code == 200, response.text
    return client


def new_client(monkeypatch, name: str) -> TestClient:
    from app.api.main import app

    c = TestClient(app)
    return sign_in(c, name)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def test_the_session_secret_exists_from_first_boot_not_first_sign_in():
    """Otherwise a fresh instance reports sessions as non-durable until
    somebody happens to log in — a health field that lies for its first
    few minutes is worse than no field."""
    lab.ensure_schema()
    assert lab.get_setting("session_secret")


def test_the_seeded_secret_is_stable_across_calls():
    lab.ensure_schema()
    first = lab.get_setting("session_secret")
    lab.ensure_schema()
    assert lab.get_setting("session_secret") == first


def test_a_session_cookie_cannot_be_forged():
    user = auth.User(email="ram@local", name="Ram", provider="local")
    cookie = auth.issue_session(user)
    assert auth.read_session(cookie).email == "ram@local"

    body, _, signature = cookie.partition(".")
    tampered = auth._b64(auth._unb64(body).replace(b"ram@local", b"eve@local")) + "." + signature
    assert auth.read_session(tampered) is None, "a rewritten payload must fail the signature check"


def test_a_session_expires():
    user = auth.User(email="ram@local")
    cookie = auth.issue_session(user)
    assert auth.read_session(cookie) is not None
    monkey = auth.SESSION_TTL_S
    try:
        auth.SESSION_TTL_S = -1
        assert auth.read_session(cookie) is None
    finally:
        auth.SESSION_TTL_S = monkey


def test_rubbish_cookies_are_anonymous_not_errors():
    for junk in ("", None, "nonsense", "a.b", "...", "x" * 500):
        assert auth.read_session(junk) is None


def test_local_sign_in_is_refused_on_a_public_instance(monkeypatch):
    monkeypatch.setenv("QTCAP_PUBLIC_MODE", "1")
    assert auth.local_login_allowed() is False
    with pytest.raises(auth.AuthError):
        auth.local_user("someone")


def test_a_public_instance_refuses_the_local_sign_in_route(monkeypatch):
    """The development bypass must not survive into the shared deployment."""
    monkeypatch.setenv("QTCAP_PUBLIC_MODE", "1")
    from app.api.main import app

    response = TestClient(app).post("/api/auth/local", json={"name": "eve"})
    assert response.status_code == 403
    assert "Google" in response.json()["detail"]


def test_google_sign_in_needs_a_client_id(monkeypatch):
    monkeypatch.delenv("QTCAP_GOOGLE_CLIENT_ID", raising=False)
    with pytest.raises(auth.AuthError) as exc:
        auth.verify_google_token("a.b.c")
    assert "not configured" in str(exc.value)


def test_a_malformed_google_token_is_rejected_before_any_network_call(monkeypatch):
    monkeypatch.setenv("QTCAP_GOOGLE_CLIENT_ID", "123.apps.googleusercontent.com")
    for bad in ("", "not-a-token", "only.two", "x" * 5000):
        with pytest.raises(auth.AuthError):
            auth.verify_google_token(bad)


def test_a_domain_allowlist_is_enforced(monkeypatch):
    monkeypatch.setenv("QTCAP_ALLOWED_EMAIL_DOMAINS", "qualitythought.in")
    assert auth.allowed_domains() == {"qualitythought.in"}


# ---------------------------------------------------------------------------
# The lab needs a session
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("method,path", [
    ("post", "/api/lab/run"), ("post", "/api/lab/verdict"), ("get", "/api/lab/summary"),
    ("get", "/api/lab/defects"), ("post", "/api/lab/defects"), ("get", "/api/lab/report"),
])
def test_every_lab_route_requires_sign_in(client, method, path):
    payload = {"case_ids": ["TC_G_G01_001"], "case_id": "TC_G_G01_001", "verdict": "pass",
               "title": "x" * 5}
    response = getattr(client, method)(path, json=payload) if method == "post" \
        else getattr(client, method)(path)
    assert response.status_code == 401


def test_the_catalogue_and_the_public_board_are_readable_signed_out(client):
    """A trainee should see what the suite contains before deciding to sign in."""
    catalogue = client.get("/api/lab/catalogue")
    assert catalogue.status_code == 200
    assert len(catalogue.json()["cases"]) == 377
    assert catalogue.json()["signed_in"] is False
    assert client.get("/api/public/defects").status_code == 200


# ---------------------------------------------------------------------------
# Isolation between trainees
# ---------------------------------------------------------------------------
def test_one_trainees_results_are_invisible_to_another(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    priya = new_client(monkeypatch, "priya")

    assert ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183"]}).status_code == 200

    assert ram.get("/api/lab/summary").json()["summary"]["executed"] == 1
    assert priya.get("/api/lab/summary").json()["summary"]["executed"] == 0

    mine = {c["id"]: c for c in ram.get("/api/lab/catalogue?suite=rag").json()["cases"]}
    theirs = {c["id"]: c for c in priya.get("/api/lab/catalogue?suite=rag").json()["cases"]}
    assert "result" in mine["TC_G_G16_183"]
    assert "result" not in theirs["TC_G_G16_183"]


def test_one_trainee_cannot_publish_or_delete_anothers_defect(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    eve = new_client(monkeypatch, "eve")

    created = ram.post("/api/lab/defects", json={"title": "A private finding", "severity": "high",
                                                 "suite": "rag"})
    defect_id = created.json()["defect"]["id"]

    assert eve.post(f"/api/lab/defects/{defect_id}/publish?publish=true").status_code == 404
    assert eve.patch(f"/api/lab/defects/{defect_id}", json={"title": "hijacked"}).status_code == 404
    assert eve.delete(f"/api/lab/defects/{defect_id}").status_code == 404
    assert eve.get("/api/lab/defects").json()["defects"] == []

    still_mine = ram.get("/api/lab/defects").json()["defects"][0]
    assert still_mine["title"] == "A private finding" and still_mine["published"] is False


def test_a_defect_is_private_until_its_author_publishes_it(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    anonymous = TestClient(__import__("app.api.main", fromlist=["app"]).app)

    created = ram.post("/api/lab/defects", json={"title": "Out-of-corpus answer", "suite": "rag"})
    defect_id = created.json()["defect"]["id"]
    assert anonymous.get("/api/public/defects").json()["defects"] == []

    ram.post(f"/api/lab/defects/{defect_id}/publish?publish=true")
    board = anonymous.get("/api/public/defects").json()["defects"]
    assert [d["id"] for d in board] == [defect_id]

    ram.post(f"/api/lab/defects/{defect_id}/publish?publish=false")
    assert anonymous.get("/api/public/defects").json()["defects"] == []


def test_the_public_board_never_carries_an_email_address(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    created = ram.post("/api/lab/defects", json={"title": "Finding", "suite": "agent"})
    ram.post(f"/api/lab/defects/{created.json()['defect']['id']}/publish?publish=true")

    board = ram.get("/api/public/defects").json()["defects"][0]
    assert "email" not in board, "a defect board is not a mailing list"
    assert board["reporter"] == "ram"


def test_a_key_pasted_into_a_defect_is_redacted_before_storage(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/defects", json={
        "title": "Key handling", "suite": "rag",
        "steps": "I used gsk_abcdefghijklmnopqrstuvwxyz012345 and it failed"})
    stored = ram.get("/api/lab/defects").json()["defects"][0]
    assert "gsk_abcdefghijklmnopqrstuvwxyz012345" not in stored["steps"]


def test_the_server_stores_no_model_key_anywhere(monkeypatch):
    """Sign-in identifies a trainee. It never gives this server their credentials."""
    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183"]},
             headers={"X-LLM-Provider": "stub", "X-LLM-Key": "gsk_" + "a" * 32})
    rows = db.all_rows("SELECT * FROM results")
    blob = " ".join(str(r) for r in rows)
    assert "gsk_" not in blob
    assert "X-LLM-Key" not in blob


# ---------------------------------------------------------------------------
# Running and marking
# ---------------------------------------------------------------------------
def test_running_a_case_stores_a_result_and_moves_the_dashboard(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    response = ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183", "TC_A_A02_011"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["summary"]["by_suite"]["rag"]["total"] == 1
    assert body["summary"]["by_suite"]["agent"]["total"] == 1


def test_a_capability_gap_is_recorded_as_an_expected_failure(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    body = ram.post("/api/lab/run", json={"case_ids": ["TC_G_G09_108"]}).json()
    assert body["results"][0]["status"] == "Fail (expected)"


def test_a_load_case_is_refused_on_a_shared_instance(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    body = ram.post("/api/lab/run", json={"case_ids": ["TC_G_G13_156"]}).json()
    assert body["results"][0]["status"] == "Blocked"
    assert "locally" in body["results"][0]["remark"]


def test_an_unknown_case_id_is_blocked_not_crashed(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    body = ram.post("/api/lab/run", json={"case_ids": ["TC_NOT_REAL_001"]}).json()
    assert body["results"][0]["status"] == "Blocked"


def test_a_batch_is_capped(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    response = ram.post("/api/lab/run", json={"case_ids": [f"TC_X_{i}" for i in range(60)]})
    assert response.status_code == 422, "an unbounded batch on a free tier is a denial of service"


def test_a_verdict_needs_a_run_behind_it(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    unrun = ram.post("/api/lab/verdict", json={"case_id": "TC_G_G01_002", "verdict": "fail"})
    assert unrun.status_code == 404

    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G01_002"]})
    marked = ram.post("/api/lab/verdict", json={"case_id": "TC_G_G01_002", "verdict": "fail"})
    assert marked.status_code == 200 and marked.json()["verdict"] == "fail"


def test_a_tester_may_disagree_with_the_harness(monkeypatch):
    """An automated check is evidence. The tester's call is the verdict."""
    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183"]})
    row = ram.post("/api/lab/verdict",
                   json={"case_id": "TC_G_G16_183", "verdict": "fail"}).json()
    assert row["status"] == "Pass" and row["verdict"] == "fail"


def test_the_report_names_failures_with_no_defect_against_them(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G03_028"]})
    report = ram.get("/api/lab/report").text
    assert "# Test report" in report
    assert "Failing cases with no defect raised" in report or "Every failure" in report


def test_only_the_latest_run_of_a_case_counts(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    for _ in range(3):
        ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183"]})
    assert ram.get("/api/lab/summary").json()["summary"]["executed"] == 1


# ---------------------------------------------------------------------------
# Built-in accounts: email and passcode, for instances with no Google client id
# ---------------------------------------------------------------------------
def test_a_passcode_is_never_stored_in_the_clear(backend):
    lab.create_account("ram@example.com", "Ram", "capstone2026")
    if backend == "sqlite":
        raw = lab.db_path().read_bytes()
        assert b"capstone2026" not in raw, "the database must hold a hash, never the passcode"
    stored = db.one("SELECT * FROM accounts WHERE email = :e", {"e": "ram@example.com"})
    assert "capstone2026" not in str(stored)
    row = db.one("SELECT * FROM accounts")
    assert len(row["passcode_hash"]) == 64 and row["iterations"] >= 100_000


def test_signing_in_needs_the_right_passcode():
    lab.create_account("ram@example.com", "Ram", "capstone2026")
    assert lab.verify_account("ram@example.com", "capstone2026")["name"] == "Ram"
    with pytest.raises(lab.AccountError):
        lab.verify_account("ram@example.com", "capstone2027")


def test_an_unknown_address_and_a_wrong_passcode_give_the_same_message():
    """Which addresses have accounts is not something a stranger gets to enumerate."""
    lab.create_account("ram@example.com", "Ram", "capstone2026")
    with pytest.raises(lab.AccountError) as wrong:
        lab.verify_account("ram@example.com", "nope12345")
    with pytest.raises(lab.AccountError) as missing:
        lab.verify_account("nobody@example.com", "nope12345")
    assert str(wrong.value) == str(missing.value)


def test_repeated_wrong_guesses_lock_the_account():
    lab.create_account("ram@example.com", "Ram", "capstone2026")
    for _ in range(lab.MAX_FAILED):
        with pytest.raises(lab.AccountError):
            lab.verify_account("ram@example.com", "wrongwrong")
    with pytest.raises(lab.AccountError) as exc:
        lab.verify_account("ram@example.com", "capstone2026")
    assert "Too many attempts" in str(exc.value), "the lock must hold even for the right passcode"


def test_a_short_passcode_is_refused():
    with pytest.raises(lab.AccountError):
        lab.create_account("ram@example.com", "Ram", "short")


def test_an_address_cannot_be_registered_twice():
    lab.create_account("ram@example.com", "Ram", "capstone2026")
    with pytest.raises(lab.AccountError) as exc:
        lab.create_account("RAM@example.com", "Impostor", "different123")
    assert "already exists" in str(exc.value)


@pytest.mark.parametrize("bad", ["", "notanemail", "no@domain", "a@b", "x" * 200 + "@y.com"])
def test_a_malformed_address_is_refused(bad):
    with pytest.raises(lab.AccountError):
        lab.create_account(bad, "X", "passcode123")


def test_sign_up_then_sign_in_through_the_api(client, monkeypatch):
    created = client.post("/api/auth/signup", json={
        "email": "priya@example.com", "name": "Priya", "passcode": "capstone2026"})
    assert created.status_code == 201
    assert created.json()["user"]["email"] == "priya@example.com"
    assert client.get("/api/auth/me").json()["user"]["provider"] == "account"

    from app.api.main import app

    fresh = TestClient(app)
    assert fresh.post("/api/auth/signin", json={"email": "priya@example.com",
                                                "passcode": "wrongwrong"}).status_code == 401
    assert fresh.post("/api/auth/signin", json={"email": "priya@example.com",
                                                "passcode": "capstone2026"}).status_code == 200


def test_accounts_work_on_a_public_instance_where_local_sign_in_does_not(monkeypatch):
    """The point of this login: a hosted instance with no Google client id is still usable."""
    monkeypatch.setenv("QTCAP_PUBLIC_MODE", "1")
    from app.api.main import app

    client = TestClient(app)
    assert client.post("/api/auth/local", json={"name": "eve"}).status_code == 403
    assert client.post("/api/auth/signup", json={
        "email": "trainee@example.com", "passcode": "capstone2026"}).status_code == 201


def test_a_short_passcode_is_told_why_in_a_sentence(monkeypatch):
    """The bug this pins: Pydantic's min_length rejected first, so the caller got
    a list of error objects, the console rendered it as text, and a trainee saw
    "[object Object]" instead of the message we wrote for them."""
    monkeypatch.setenv("QTCAP_PUBLIC_MODE", "1")
    from app.api.main import app

    response = TestClient(app).post(
        "/api/auth/signup", json={"email": "short@example.com", "passcode": "abc123"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert "8 characters" in detail


def test_every_validation_failure_answers_with_a_string_not_a_dump(monkeypatch):
    """A list of objects in `detail` is what produces "[object Object]" in any
    caller that renders it. One handler makes that impossible service-wide."""
    from app.api.main import app

    client = TestClient(app)
    for payload in ({"email": "x"}, {"passcode": "capstone2026"}, {}):
        body = client.post("/api/auth/signup", json=payload).json()
        assert isinstance(body["detail"], str), payload
        assert "object" not in body["detail"].lower()


def test_the_account_page_carries_history_defects_and_totals(monkeypatch):
    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183", "TC_A_A02_011"]})
    ram.post("/api/lab/defects", json={"title": "A finding", "suite": "rag"})

    body = ram.get("/api/lab/account").json()
    assert body["summary"]["executed"] == 2
    assert len(body["history"]) == 2
    assert len(body["defects"]) == 1
    assert {"case_id", "status", "created_at"} <= set(body["history"][0])


def test_the_csv_report_is_a_real_csv(monkeypatch):
    import csv
    import io

    ram = new_client(monkeypatch, "ram")
    ram.post("/api/lab/run", json={"case_ids": ["TC_G_G16_183"]})
    rows = list(csv.reader(io.StringIO(ram.get("/api/lab/report.csv").text)))
    assert rows[0][:5] == ["case_id", "suite", "area", "harness_status", "my_verdict"]
    assert rows[1][0] == "TC_G_G16_183"


def test_sign_in_attempts_are_rate_limited(monkeypatch):
    """Sign-in is the one endpoint worth guessing at, so it gets its own budget."""
    monkeypatch.setenv("QTCAP_PUBLIC_MODE", "1")
    from app.api.hosting import LIMITER
    from app.api.main import app

    LIMITER.windows.clear()
    LIMITER.auth_per_minute = 3
    client = TestClient(app)
    try:
        codes = [client.post("/api/auth/signin",
                             json={"email": "x@example.com", "passcode": "guessing123"}).status_code
                 for _ in range(6)]
        assert 429 in codes, "unlimited passcode guesses is not a login, it is a piñata"
    finally:
        LIMITER.auth_per_minute = 30
        LIMITER.windows.clear()


def test_sign_in_has_its_own_budget_not_the_heavy_one():
    """A class behind one NAT must not lock itself out after eight people log in."""
    from app.api.hosting import RateLimiter

    limiter = RateLimiter()
    assert limiter.auth_per_minute > limiter.heavy_per_minute
    for _ in range(limiter.heavy_per_minute + 2):
        assert limiter.check("shared-nat", bucket="auth")[0] is True
