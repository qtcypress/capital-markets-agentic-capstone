"""FastAPI service exposing all three applications plus the tester's endpoints.

Deployment model
----------------
This runs in two shapes from one codebase:

  LOCAL    one student, one machine. Provider and key come from the environment,
           Ollama works, guardrail mode is a server setting, no rate limits.

  HOSTED   one URL, a whole class. Each student supplies their own free API key
           from the browser on every request; the server stores no keys, and the
           guardrail mode is per request so one student's red-team lab cannot
           disable another student's controls. Set QTCAP_PUBLIC_MODE=1.

Routes
------
  GET  /                      the web console
  GET  /api/health            liveness + configuration snapshot
  GET  /api/config            effective configuration (never secrets)
  GET  /api/providers         model providers a student can bring a key for
  POST /api/llm/verify        check a student's key works, without storing it
  POST /api/rag/query         RAG application
  POST /api/agent/query       single tool-calling agent
  POST /api/multi/query       MCP multi-agent system
  GET  /api/tools             tool catalogue with JSON Schemas
  POST /api/tools/{name}      direct tool invocation (contract testing)
  GET  /api/mcp/servers       MCP server inventory and routing table
  POST /api/mcp/call          direct MCP tool call
  GET  /api/market/{symbol}   raw market payload with provenance
  GET  /api/kb/stats          corpus statistics (including this caller's uploads)
  POST /api/kb/search         raw retrieval, no generation
  GET  /api/rag/documents     documents this browser has added to its corpus
  POST /api/rag/documents     add a document to this browser's corpus
  DELETE /api/rag/documents            remove every document this browser added
  DELETE /api/rag/documents/{doc_id}   remove one
  GET  /api/tests/suites      available suites, categories and case counts
  POST /api/tests/run         run a suite subset in the browser
  GET  /api/issues            list filed findings
  POST /api/issues            file a finding (optionally notifies a webhook)
  PATCH /api/issues/{id}      update status, severity or impact
  GET  /api/issues/export     download findings as markdown, csv or json
  GET  /api/issues/stats      finding counts by severity and area
"""
from __future__ import annotations

import os
import time
from typing import Any

from fastapi import Cookie, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import auth, db as database, issues as issue_store, lab
from ..agents.orchestrator import Orchestrator
from ..agents.single_agent import SingleAgent
from ..agents.tools import REGISTRY, execute_tool
from ..config import ROOT, get_config
from ..llm.registry import public_catalogue
from ..llm.session import LLMSessionError, build_from_request, redact
from ..market import get_fx_rate, get_option_chain, get_quote, list_supported_symbols
from ..mcpsvc import MCPSession
from ..rag import get_pipeline, get_store
from ..rag.corpus import REGISTRY as CORPUS, DocumentError
from .hosting import guard_request, public_mode, safe_error

WEB_DIR = ROOT / "app" / "web"

app = FastAPI(
    title="Quality Thought — Capital Markets Agentic Capstone",
    version="1.1.0",
    description="RAG, single agent and MCP multi-agent applications for AI testing practice.",
)

_state: dict[str, Any] = {}


def _rag():
    if "rag" not in _state:
        _state["rag"] = get_pipeline()
    return _state["rag"]


def _agent():
    if "agent" not in _state:
        _state["agent"] = SingleAgent()
    return _state["agent"]


def _orch():
    if "orch" not in _state:
        _state["orch"] = Orchestrator(transport=os.environ.get("QTCAP_MCP_TRANSPORT", "in_process"))
    return _state["orch"]


def _mcp():
    if "mcp" not in _state:
        _state["mcp"] = MCPSession.start(os.environ.get("QTCAP_MCP_TRANSPORT", "in_process"))
    return _state["mcp"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    top_k: int | None = Field(None, ge=1, le=20)
    category: str | None = None
    # Per-request guardrail mode. None means "use the server default"; False is
    # the deliberately vulnerable build used by the red-team labs, and it applies
    # to this request only.
    guardrails: bool | None = None


class ToolRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class MCPCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(4, ge=1, le=20)
    min_score: float = Field(0.0, ge=0.0, le=1.0)


class VerifyRequest(BaseModel):
    prompt: str = Field("Reply with the single word: ready", max_length=500)


class TestRunRequest(BaseModel):
    suite: str | None = Field(None, pattern="^(blue|red)$")
    category: str | None = Field(None, max_length=60)
    case_id: str | None = Field(None, max_length=60)
    limit: int = Field(25, ge=1, le=120)
    use_my_model: bool = False


class IssueRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    area: str = "other"
    severity: str = "medium"
    summary: str = ""
    steps: str = ""
    expected: str = ""
    actual: str = ""
    impact: str = ""
    case_id: str = ""
    reporter: str = ""
    tags: list[str] = Field(default_factory=list)


class IssuePatch(BaseModel):
    status: str | None = None
    severity: str | None = None
    impact: str | None = None
    title: str | None = None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.middleware("http")(guard_request)


@app.middleware("http")
async def timing(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time-Ms"] = str(int((time.perf_counter() - started) * 1000))
    response.headers["X-App-Version"] = app.version
    return response


# ---------------------------------------------------------------------------
# Bring-your-own-key plumbing
# ---------------------------------------------------------------------------
def _llm_from_headers(
    provider: str | None,
    model: str | None,
    api_key: str | None,
):
    """Build a client for this request only.

    The key arrives in a header, is used once, and is never written anywhere. It
    is deliberately not accepted as a query parameter, because query strings end
    up in access logs.
    """
    try:
        return build_from_request(provider, model, api_key)
    except LLMSessionError as exc:
        raise HTTPException(400, str(exc)) from exc


def _llm_headers(
    x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
    x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
    x_llm_key: str | None = Header(None, alias="X-LLM-Key"),
):
    return x_llm_provider, x_llm_model, x_llm_key


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    cfg = get_config(refresh=True)
    return {
        "status": "ok",
        "version": app.version,
        "mode": "hosted" if public_mode() else "local",
        "server_llm_provider": cfg.llm.provider,
        "byok": True,
        "market_mode": cfg.market.mode,
        "guardrails_default": cfg.guardrails_enabled and not cfg.vulnerable_mode,
        "knowledge_chunks": get_store().stats()["chunks"],
        "tools": len(REGISTRY),
        "issues_open": issue_store.stats()["open"],
        "storage": database.describe()["backend"],
        "storage_durable": database.describe()["persistent"],
    }


@app.get("/api/config")
def config():
    cfg = get_config(refresh=True)
    return {
        "mode": "hosted" if public_mode() else "local",
        "llm": {"server_default": cfg.llm.provider, "temperature": cfg.llm.temperature,
                "max_tokens": cfg.llm.max_tokens},
        "market": {"mode": cfg.market.mode, "allow_stale": cfg.market.allow_stale,
                   "risk_free_rate": cfg.market.risk_free_rate},
        "rag": {"top_k": cfg.rag_top_k, "min_score": cfg.rag_min_score},
        "agent": {"max_steps": cfg.agent_max_steps},
        "guardrails": {"default_enabled": cfg.guardrails_enabled and not cfg.vulnerable_mode,
                       "per_request": True},
        "supported_symbols": list_supported_symbols(),
    }


@app.get("/api/providers")
def providers():
    """Public catalogue. Contains no keys — only what the browser needs to
    render the picker and point a student at a free signup page."""
    return {
        "providers": public_catalogue(),
        "recommended": "groq",
        "offline_default": "stub",
        "note": (
            "Your key is sent with each request, used once, and never stored on this server. "
            "Ollama only works when you run this project on your own machine."
        ),
    }


@app.post("/api/llm/verify")
def verify_llm(req: VerifyRequest, llm_headers=None,
               x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
               x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
               x_llm_key: str | None = Header(None, alias="X-LLM-Key")):
    """Round-trip one tiny completion so a student can confirm their key works
    before they spend a lab on a 401."""
    from ..llm import Message

    llm, choice = _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)
    resp = llm.complete([Message("user", req.prompt)])
    return {
        "ok": resp.ok,
        **choice.describe(),
        "latency_ms": resp.latency_ms,
        "reply": redact(resp.text)[:300] if resp.ok else "",
        "error": redact(resp.error) if resp.error else None,
    }


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
@app.post("/api/rag/query")
def rag_query(req: QueryRequest,
              x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
              x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
              x_llm_key: str | None = Header(None, alias="X-LLM-Key"),
              x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    llm, choice = _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)
    result = _rag().answer(req.query, top_k=req.top_k, category=req.category,
                           llm=llm, enforce=req.guardrails, corpus=x_corpus)
    payload = result.to_dict()
    for c in payload["contexts"]:
        c["text"] = c["text"][:1200]
    payload["error"] = redact(payload["error"]) if payload["error"] else None
    payload["backend"] = choice.describe()
    return payload


@app.post("/api/agent/query")
def agent_query(req: QueryRequest,
                x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
                x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
                x_llm_key: str | None = Header(None, alias="X-LLM-Key")):
    llm, choice = _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)
    payload = _agent().run(req.query, llm=llm, enforce=req.guardrails).to_dict()
    payload["error"] = redact(payload["error"]) if payload.get("error") else None
    payload["backend"] = choice.describe()
    return payload


@app.post("/api/multi/query")
def multi_query(req: QueryRequest,
                x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
                x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
                x_llm_key: str | None = Header(None, alias="X-LLM-Key")):
    llm, choice = _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)
    payload = _orch().run(req.query, llm=llm, enforce=req.guardrails).to_dict()
    payload["error"] = redact(payload["error"]) if payload.get("error") else None
    payload["backend"] = choice.describe()
    return payload


# ---------------------------------------------------------------------------
# Tools and MCP
# ---------------------------------------------------------------------------
@app.get("/api/tools")
def tools():
    return {
        "count": len(REGISTRY),
        "tools": [{**t.schema(), "risk": t.risk, "domain": t.domain} for t in REGISTRY.values()],
    }


@app.post("/api/tools/{name}")
def call_tool(name: str, req: ToolRequest):
    result = execute_tool(name, req.arguments)
    status = 200 if result["ok"] else 422
    if (result.get("error") or {}).get("code") == "unknown_tool":
        status = 404
    return JSONResponse(result, status_code=status)


@app.get("/api/mcp/servers")
def mcp_servers():
    session = _mcp()
    return {
        "transport": session.transport,
        "servers": [
            {"key": key, **info, "tools": [t["name"] for t in session.clients[key].list_tools()]}
            for key, info in session.server_info.items()
        ],
        "routing": session.routing,
    }


@app.post("/api/mcp/call")
def mcp_call(req: MCPCallRequest):
    record = _mcp().call(req.tool, req.arguments)
    body = {
        "ok": record.ok, "server": record.server, "tool": record.tool,
        "arguments": record.arguments, "transport": record.transport,
        "duration_ms": record.duration_ms, "result": record.result, "error": record.error,
    }
    return JSONResponse(body, status_code=200 if record.ok else 422)


# ---------------------------------------------------------------------------
# Market and knowledge base
# ---------------------------------------------------------------------------
@app.get("/api/market/{symbol}")
def market(symbol: str, kind: str = "quote", expiry: str | None = None):
    try:
        if kind == "quote":
            payload = get_quote(symbol)
        elif kind == "option_chain":
            payload = get_option_chain(symbol, expiry)
        elif kind == "fx":
            payload = get_fx_rate(symbol[:3], symbol[3:6] or "INR")
        else:
            raise HTTPException(400, f"unknown kind '{kind}'")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"market data unavailable: {redact(exc)}") from exc
    return payload.to_dict()


@app.get("/api/kb/stats")
def kb_stats(x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    stats = CORPUS.store_for(x_corpus).stats()
    stats["uploaded"] = CORPUS.stats(x_corpus)
    return stats


# ---------------------------------------------------------------------------
# Documents a trainee adds to the corpus
# ---------------------------------------------------------------------------
# Every one of these is scoped by the X-QTCAP-Corpus header the console
# generates per browser. No header, no documents — and one student's uploads are
# never visible to another, which is asserted in tests/test_documents.py rather
# than merely intended here.
class DocumentRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=400_000)


@app.get("/api/rag/documents")
def list_documents(x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    return {"documents": CORPUS.documents(x_corpus), "stats": CORPUS.stats(x_corpus)}


@app.post("/api/rag/documents", status_code=201)
def add_document(req: DocumentRequest,
                 x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    try:
        doc = CORPUS.add(x_corpus, req.filename, req.content)
    except DocumentError as exc:
        # 422, not 500: the document was understood and refused, and the message
        # says what to do about it.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"document": doc, "stats": CORPUS.stats(x_corpus),
            "kb": CORPUS.store_for(x_corpus).stats()}


@app.delete("/api/rag/documents/{doc_id}")
def remove_document(doc_id: str, x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    if not CORPUS.remove(x_corpus, doc_id):
        raise HTTPException(status_code=404, detail=f"No document {doc_id} in this corpus.")
    return {"removed": doc_id, "stats": CORPUS.stats(x_corpus)}


@app.delete("/api/rag/documents")
def clear_documents(x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    return {"removed": CORPUS.clear(x_corpus), "stats": CORPUS.stats(x_corpus)}


@app.post("/api/kb/search")
def kb_search(req: SearchRequest, x_corpus: str | None = Header(None, alias="X-QTCAP-Corpus")):
    hits = CORPUS.store_for(x_corpus).search(req.query, top_k=req.top_k, min_score=req.min_score)
    return {
        "query": req.query,
        "count": len(hits),
        "results": [
            {"doc_id": h["chunk"].doc_id, "section": h["chunk"].section, "score": h["score"],
             "rank": h["rank"], "category": h["chunk"].category, "authority": h["chunk"].authority,
             "chunk_id": h["chunk"].chunk_id, "excerpt": h["chunk"].text[:600]}
            for h in hits
        ],
    }


# ---------------------------------------------------------------------------
# In-browser test runner
# ---------------------------------------------------------------------------
@app.get("/api/tests/suites")
def test_suites():
    from tests.runner.harness import load_cases

    cases = load_cases()
    by_suite: dict[str, dict[str, int]] = {}
    for c in cases:
        entry = by_suite.setdefault(c.get("suite", "?"), {"total": 0})
        entry["total"] += 1
        cat = c.get("category", "uncategorised")
        entry[cat] = entry.get(cat, 0) + 1
    return {
        "total": len(cases),
        "suites": by_suite,
        "categories": sorted({c.get("category", "uncategorised") for c in cases}),
        "max_per_run": 120,
    }


@app.post("/api/tests/run")
def run_tests(req: TestRunRequest,
              x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
              x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
              x_llm_key: str | None = Header(None, alias="X-LLM-Key")):
    """Run a slice of the suite from the browser.

    Bounded by `limit` because on a free hosting tier a full 327-case run with a
    real model would exhaust both the request timeout and the student's provider
    quota. The full suite is a local command; this endpoint is for demonstrating
    and for filing findings from a failure.
    """
    from tests.runner.harness import load_cases, run_case, summarise

    cases = load_cases(req.suite)
    if req.case_id:
        cases = [c for c in cases if c.get("id") == req.case_id]
    if req.category:
        cases = [c for c in cases if c.get("category") == req.category]
    if not cases:
        raise HTTPException(404, "No cases matched that filter.")
    truncated = len(cases) > req.limit
    cases = cases[: req.limit]

    backend = {"provider": "stub", "model": "deterministic-stub-v1", "key_supplied": False}
    if req.use_my_model:
        # Running the suite against the student's own model is the point of the
        # model-comparison lab, but it spends their quota, so it is opt-in.
        _, choice = _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)
        backend = choice.describe()
        os.environ["QTCAP_SUITE_BACKEND"] = choice.provider

    results = [run_case(c) for c in cases]
    slim = [
        {k: v for k, v in r.items() if k != "result"}
        | {"answer": redact(str((r.get("result") or {}).get("answer", ""))[:600])}
        for r in results
    ]
    return {
        "summary": summarise(results),
        "results": slim,
        "truncated": truncated,
        "backend": backend,
        "note": "Run the full suite locally with ./test.sh fast — this endpoint is capped.",
    }


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
@app.get("/api/issues")
def get_issues(status: str | None = None, severity: str | None = None,
               area: str | None = None, limit: int = 200):
    return {"issues": issue_store.list_issues(status, severity, area, min(limit, 500)),
            "stats": issue_store.stats()}


@app.post("/api/issues")
def post_issue(req: IssueRequest):
    try:
        issue = issue_store.create_issue(req.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"issue": issue.to_dict(), "stats": issue_store.stats()}


@app.patch("/api/issues/{issue_id}")
def patch_issue(issue_id: str, req: IssuePatch):
    changes = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = issue_store.update_issue(issue_id, changes)
    if updated is None:
        raise HTTPException(404, f"No issue '{issue_id}'.")
    return {"issue": updated}


@app.get("/api/issues/stats")
def issue_stats():
    return issue_store.stats()


@app.get("/api/issues/export")
def export_issues(fmt: str = "markdown"):
    rows = issue_store.list_issues(limit=2000)
    if fmt == "json":
        return JSONResponse(rows, headers={"Content-Disposition": "attachment; filename=findings.json"})
    if fmt == "csv":
        return PlainTextResponse(issue_store.to_csv(rows), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=findings.csv"})
    return PlainTextResponse(issue_store.to_markdown(rows), media_type="text/markdown",
                             headers={"Content-Disposition": "attachment; filename=findings.md"})


# ---------------------------------------------------------------------------
# Test lab: sign in, run the published catalogue, keep results and defects
# ---------------------------------------------------------------------------
# Everything under /api/lab is scoped to the signed-in account, with one
# deliberate exception: the published defect board, which anyone may read. A
# model key is never part of this — it stays in the browser and arrives as a
# header on each request, exactly as it did before sign-in existed.
CATALOGUE_PATH = ROOT / "app" / "data" / "catalogue.json"
_CATALOGUE: dict[str, Any] | None = None


def _catalogue() -> dict[str, Any]:
    global _CATALOGUE
    if _CATALOGUE is None:
        import json

        if not CATALOGUE_PATH.exists():
            _CATALOGUE = {"cases": [], "areas": [], "counts": {"total": 0},
                          "error": "catalogue.json not built — run tools/export_catalogue.py"}
        else:
            _CATALOGUE = json.loads(CATALOGUE_PATH.read_text())
        _CATALOGUE["by_id"] = {c["id"]: c for c in _CATALOGUE.get("cases", [])}
    return _CATALOGUE


def _require_user(cookie: str | None) -> auth.User:
    user = auth.read_session(cookie)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to use the test lab.")
    return user


def _set_session_cookie(response: Response, user: auth.User) -> None:
    response.set_cookie(
        auth.COOKIE_NAME, auth.issue_session(user), max_age=auth.SESSION_TTL_S,
        httponly=True, samesite="lax", secure=public_mode(), path="/",
    )


class GoogleSignIn(BaseModel):
    credential: str = Field(..., min_length=20, max_length=4096)


class LocalSignIn(BaseModel):
    name: str = Field("trainee", min_length=1, max_length=40)


class AccountSignUp(BaseModel):
    email: str = Field(..., min_length=5, max_length=160)
    name: str = Field("", max_length=80)
    passcode: str = Field(..., min_length=8, max_length=200)


class AccountSignIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=160)
    passcode: str = Field(..., min_length=1, max_length=200)


class VerdictRequest(BaseModel):
    case_id: str = Field(..., min_length=3, max_length=40)
    verdict: str = Field(..., pattern="^(pass|fail|blocked|not_run)$")


class DefectRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    severity: str = Field("medium", pattern="^(critical|high|medium|low)$")
    suite: str = Field("rag", pattern="^(rag|agent|multi)$")
    case_id: str | None = Field(None, max_length=40)
    steps: str = Field("", max_length=4000)
    expected: str = Field("", max_length=2000)
    actual: str = Field("", max_length=4000)


class DefectPatch(BaseModel):
    title: str | None = Field(None, max_length=200)
    severity: str | None = Field(None, pattern="^(critical|high|medium|low)$")
    status: str | None = Field(None, pattern="^(open|triaged|fixed|rejected)$")
    steps: str | None = Field(None, max_length=4000)
    expected: str | None = Field(None, max_length=2000)
    actual: str | None = Field(None, max_length=4000)


class RunRequest(BaseModel):
    case_ids: list[str] = Field(..., min_length=1, max_length=40)


@app.get("/api/auth/config")
def auth_config():
    config = auth.auth_config()
    config["accounts_enabled"] = True
    config["min_passcode"] = lab.MIN_PASSCODE
    storage = database.describe()
    config["storage"] = storage["backend"]
    # The UI says this out loud rather than letting a class discover it when a
    # redeploy deletes their accounts.
    config["durable"] = storage["persistent"]
    config["sessions_survive_restart"] = auth.secret_is_durable()
    return config


@app.post("/api/auth/google")
def auth_google(req: GoogleSignIn, response: Response):
    try:
        user = auth.verify_google_token(req.credential)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, user)
    return {"user": user.public()}


@app.post("/api/auth/local")
def auth_local(req: LocalSignIn, response: Response):
    """Offline sign-in. Refused outright on a public instance."""
    try:
        user = auth.local_user(req.name)
    except auth.AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    _set_session_cookie(response, user)
    return {"user": user.public()}


@app.post("/api/auth/signup", status_code=201)
def auth_signup(req: AccountSignUp, response: Response, request: Request):
    """Create an account on this instance: an email address and a passcode.

    The passcode is hashed with PBKDF2 and never stored in the clear. The email
    address is not verified — see the note in app/lab.py about what that does
    and does not buy you.
    """
    _signup_limit(request)
    try:
        account = lab.create_account(req.email, req.name, req.passcode)
    except lab.AccountError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = auth.User(email=account["email"], name=account["name"], provider="account")
    _set_session_cookie(response, user)
    return {"user": user.public()}


@app.post("/api/auth/signin")
def auth_signin(req: AccountSignIn, response: Response, request: Request):
    _signup_limit(request)
    try:
        account = lab.verify_account(req.email, req.passcode)
    except lab.AccountError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = auth.User(email=account["email"], name=account["name"], provider="account")
    _set_session_cookie(response, user)
    return {"user": user.public()}


def _signup_limit(request: Request) -> None:
    """Sign-in is the one endpoint worth guessing against, so it gets its own budget."""
    from .hosting import LIMITER, client_id

    allowed, limit, retry = LIMITER.check(client_id(request), bucket="auth")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many sign-in attempts from this address. Try again in {retry}s.",
            headers={"Retry-After": str(retry)})


@app.get("/api/auth/me")
def auth_me(qtcap_session: str | None = Cookie(None)):
    user = auth.read_session(qtcap_session)
    return {"user": user.public() if user else None,
            "config": auth.auth_config()}


@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/lab/catalogue")
def lab_catalogue(suite: str | None = None, area: str | None = None,
                  qtcap_session: str | None = Cookie(None)):
    """The published IEEE suite. Readable signed out — running it is not."""
    data = _catalogue()
    cases = data.get("cases", [])
    if suite:
        cases = [c for c in cases if c["suite"] == suite]
    if area:
        cases = [c for c in cases if c["area"] == area]
    user = auth.read_session(qtcap_session)
    results = lab.latest_results(user.email) if user else {}
    merged = []
    for case in cases:
        row = dict(case)
        result = results.get(case["id"])
        if result:
            row["result"] = {"status": result["status"], "verdict": result["verdict"],
                             "actual": result["actual"][:400], "remark": result["remark"][:400],
                             "created_at": result["created_at"],
                             "duration_ms": result["duration_ms"]}
        merged.append(row)
    return {"cases": merged, "areas": data.get("areas", []), "counts": data.get("counts", {}),
            "signed_in": bool(user)}


@app.post("/api/lab/run")
def lab_run(req: RunRequest,
            qtcap_session: str | None = Cookie(None),
            x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
            x_llm_model: str | None = Header(None, alias="X-LLM-Model"),
            x_llm_key: str | None = Header(None, alias="X-LLM-Key")):
    """Execute up to forty published cases and store the results for this user."""
    import time as _time
    import uuid as _uuid

    user = _require_user(qtcap_session)
    # Touch the model headers so an invalid key fails here, with a clear message,
    # rather than forty times inside the executors.
    _llm_from_headers(x_llm_provider, x_llm_model, x_llm_key)

    from tests.ieee.executors import EXECUTORS

    catalogue = _catalogue()
    run_id = _uuid.uuid4().hex[:12]
    rows = []
    for case_id in req.case_ids:
        case = catalogue["by_id"].get(case_id)
        if case is None:
            rows.append({"case_id": case_id, "status": "Blocked",
                         "remark": "No such case in the published catalogue."})
            continue
        if not case.get("runnable"):
            rows.append({"case_id": case_id, "status": "Blocked",
                         "remark": "This case spawns load and is disabled on a shared instance. "
                                   "Run it locally with tools/run_ieee_suite.py."})
            continue
        executor = EXECUTORS.get(case["executor"])
        if executor is None:
            rows.append({"case_id": case_id, "status": "Blocked",
                         "remark": f"No executor named {case['executor']}."})
            continue
        binding = _binding_for(case_id)
        started = _time.perf_counter()
        try:
            outcome = executor(binding)
        except Exception as exc:  # noqa: BLE001
            from tests.ieee.executors import Outcome

            outcome = Outcome("Fail", f"{type(exc).__name__}: {redact(str(exc))[:300]}", {},
                              "The case raised an unhandled exception. Read it before assuming "
                              "the harness is at fault.")
        elapsed = (_time.perf_counter() - started) * 1000
        stored = lab.record_result(user.email, case, outcome, elapsed, run_id)
        rows.append({"case_id": case_id, "status": stored["status"],
                     "actual": stored["actual"][:500], "remark": stored["remark"][:400],
                     "duration_ms": stored["duration_ms"], "capability": case["capability"]})
    return {"run_id": run_id, "results": rows, "summary": lab.summary(user.email)}


_BINDINGS: dict[str, Any] | None = None


def _binding_for(case_id: str) -> dict[str, Any]:
    global _BINDINGS
    if _BINDINGS is None:
        import yaml

        path = ROOT / "tests" / "ieee" / "bindings.yaml"
        _BINDINGS = yaml.safe_load(path.read_text()) if path.exists() else {}
    return dict(_BINDINGS.get(case_id) or {})


@app.post("/api/lab/verdict")
def lab_verdict(req: VerdictRequest, qtcap_session: str | None = Cookie(None)):
    """The tester's own call. It may disagree with the harness, and that is allowed."""
    user = _require_user(qtcap_session)
    row = lab.set_verdict(user.email, req.case_id, req.verdict)
    if row is None:
        raise HTTPException(status_code=404,
                            detail="Run the case before marking it — a verdict needs evidence.")
    return {"case_id": req.case_id, "verdict": row["verdict"], "status": row["status"]}


@app.get("/api/lab/summary")
def lab_summary(qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    return {"user": user.public(), "summary": lab.summary(user.email)}


@app.get("/api/lab/account")
def lab_account(qtcap_session: str | None = Cookie(None)):
    """Everything the My Account page shows: profile, run history, defects, totals."""
    user = _require_user(qtcap_session)
    latest = lab.latest_results(user.email)
    history = sorted(latest.values(), key=lambda r: r["created_at"], reverse=True)
    return {
        "user": user.public(),
        "summary": lab.summary(user.email),
        "defects": lab.my_defects(user.email),
        "history": [
            {"case_id": r["case_id"], "suite": r["suite"], "area": r["area"],
             "status": r["status"], "verdict": r["verdict"], "remark": r["remark"][:300],
             "actual": r["actual"][:300], "duration_ms": r["duration_ms"],
             "created_at": r["created_at"]}
            for r in history[:400]
        ],
    }


@app.get("/api/lab/report.csv")
def lab_report_csv(qtcap_session: str | None = Cookie(None)):
    """The same report as a spreadsheet, because that is what gets emailed."""
    import csv
    import io

    user = _require_user(qtcap_session)
    latest = lab.latest_results(user.email)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["case_id", "suite", "area", "harness_status", "my_verdict",
                     "duration_ms", "executed_at", "actual", "remark"])
    for row in sorted(latest.values(), key=lambda r: r["case_id"]):
        writer.writerow([row["case_id"], row["suite"], row["area"], row["status"],
                         row["verdict"] or "", round(row["duration_ms"]),
                         time.strftime("%Y-%m-%d %H:%M", time.localtime(row["created_at"])),
                         row["actual"][:500], row["remark"][:500]])
    return PlainTextResponse(
        buffer.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=test-results.csv"})


@app.get("/api/lab/report")
def lab_report(qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    return PlainTextResponse(
        lab.export_markdown(user.email, user.name), media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=test-report.md"})


@app.get("/api/lab/defects")
def lab_my_defects(qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    return {"defects": lab.my_defects(user.email)}


@app.post("/api/lab/defects", status_code=201)
def lab_raise_defect(req: DefectRequest, qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    try:
        return {"defect": lab.raise_defect(user.email, user.name, req.model_dump())}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/lab/defects/{defect_id}")
def lab_update_defect(defect_id: str, req: DefectPatch,
                      qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    row = lab.update_defect(user.email, defect_id, req.model_dump(exclude_none=True))
    if row is None:
        raise HTTPException(status_code=404, detail="No such defect of yours.")
    return {"defect": row}


@app.post("/api/lab/defects/{defect_id}/publish")
def lab_publish_defect(defect_id: str, publish: bool = True,
                       qtcap_session: str | None = Cookie(None)):
    """Move a defect onto the public board, or take it back off it."""
    user = _require_user(qtcap_session)
    row = lab.set_published(user.email, defect_id, publish)
    if row is None:
        raise HTTPException(status_code=404, detail="No such defect of yours.")
    return {"defect": row}


@app.delete("/api/lab/defects/{defect_id}")
def lab_delete_defect(defect_id: str, qtcap_session: str | None = Cookie(None)):
    user = _require_user(qtcap_session)
    if not lab.delete_defect(user.email, defect_id):
        raise HTTPException(status_code=404, detail="No such defect of yours.")
    return {"deleted": defect_id}


@app.get("/api/public/defects")
def public_defect_board(limit: int = 200):
    """The shared board: published defects only, with email addresses stripped."""
    return {"defects": lab.public_defects(limit)}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index():
    idx = WEB_DIR / "index.html"
    if not idx.exists():
        return {"message": "UI not built. API is available under /api."}
    return FileResponse(str(idx))


# Browsers and link previewers ask for these at the site root, not under
# /static, and a 404 on a favicon is the kind of thing nobody notices until a
# trainee asks why the tab is blank.
@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/logo.svg", include_in_schema=False)
def brand_asset(request: Request):
    asset = WEB_DIR / request.url.path.lstrip("/")
    if not asset.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(asset))


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    """Never let a raw exception string reach a caller — it may carry a key."""
    return JSONResponse(safe_error(exc), status_code=500)
