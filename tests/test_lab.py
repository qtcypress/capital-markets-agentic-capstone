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

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, lab  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    monkeypatch.setenv("QTCAP_DB_PATH", str(tmp_path / "lab.sqlite3"))
    lab._CONN = None
    lab.reset()
    yield
    lab._CONN = None


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
    with lab._LOCK:
        rows = lab._connect().execute("SELECT * FROM results").fetchall()
    blob = " ".join(str(dict(r)) for r in rows)
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
