# Architecture

Every design decision in this project was made twice: once for the application to
work, and once for it to be *testable*. This document explains both, because the
second reason is what you are here to learn.

---

## The layer stack

```
                        ┌───────────────────────────┐
                        │  Web console (app/web)    │
                        │  publishes state attrs    │
                        └─────────────┬─────────────┘
                                      │ HTTP/JSON
                        ┌─────────────▼─────────────┐
                        │  FastAPI (app/api)        │
                        └─────────────┬─────────────┘
          ┌───────────────────────────┼───────────────────────────┐
    ┌─────▼──────┐            ┌───────▼───────┐          ┌────────▼────────┐
    │    RAG     │            │ Single agent  │          │  Orchestrator   │
    │ (app/rag)  │            │ (app/agents)  │          │  (app/agents)   │
    └─────┬──────┘            └───────┬───────┘          └────────┬────────┘
          │                           │                            │ MCP
          │                           │                  ┌─────────▼─────────┐
          │                           │                  │ 3 MCP servers     │
          │                           │                  │ (app/mcpsvc)      │
          │                           │                  └─────────┬─────────┘
          └───────────┬───────────────┴────────────────────────────┘
                      │
        ┌─────────────▼──────────────┬──────────────────┬────────────────┐
        │ Guardrails                 │ Tool registry    │ LLM providers  │
        │ (app/guardrails)           │ (app/agents)     │ (app/llm)      │
        └─────────────┬──────────────┴────────┬─────────┴────────────────┘
                      │                       │
        ┌─────────────▼───────────┐  ┌─────────▼──────────┐
        │ Knowledge base + index  │  │ Market data layer  │
        │ (app/rag/store.py)      │  │ (app/market)       │
        └─────────────────────────┘  └────────────────────┘
```

---

## Why each layer is shaped the way it is

### The LLM is behind an interface, not a dependency

`app/llm/base.py` defines one narrow contract: messages in, text and tool calls
out. Four backends implement it — OpenAI-compatible, Anthropic, Ollama, and a
deterministic stub.

**Testing consequence:** the same 321 cases run against a cloud model, a local
model, or the stub, unchanged. When a test fails on one backend and passes on
another, the difference is isolated to the model, because nothing else moved.

The stub deserves a note. It is rule-based: regular expressions route a query to
a tool, and answers are extracted from the supplied context rather than
generated. That makes it useless as a product and invaluable as a fixture,
because it turns "did the pipeline wire up correctly" into a question with a
stable answer. It is also deliberately naive about instructions found in
context, which is what lets the red-team labs demonstrate a real failure when
guardrails are disabled.

### Market data declares its own provenance

`app/market/sources.py` tries live APIs first, falls back to a recorded snapshot,
and finally to a labelled synthetic generator. Every response is a
`MarketPayload` carrying `source`, `provider`, `as_of`, `stale` and `warnings`.

**Testing consequence:** this is the difference between a suite that works and
one that is abandoned after three weeks. A test asserting `last_price == 24800`
fails every day. A test asserting `source in (live, snapshot, synthetic)` and
`lot_size == 75` passes forever and still catches the failure that matters —
stale data being served as though it were fresh.

The habit generalises. In any AI system you test, find the boundary where
external data enters and insist it carries provenance. If it does not, that is
your first defect report.

### Derivatives maths is pure

`app/market/derivatives.py` has no I/O, no randomness, and no clock. Given the
same inputs it returns the same numbers to the last decimal.

**Testing consequence:** it is the one place in an AI system where classical,
exact assertions apply — and therefore the right place for a manual tester to
write their first automated test. `black_scholes(24800, 24800, 30/365, 0.065,
0.14, "call")["price"] == 465.59` is a test you already know how to write. Start
there, build confidence, then move outward into the fuzzy layers.

The module also encodes invariants that hold regardless of inputs: a call delta
between 0 and 1, gamma positive, put-call parity, unlimited loss on a naked
short call. Invariants are how you write a meaningful assertion about a value
you cannot predict — the single most transferable idea in this project.

### Retrieval is hybrid and inspectable

`app/rag/store.py` chunks on `##` headings so each chunk is a self-contained
section, then scores with BM25 fused with TF-IDF cosine similarity. No external
embedding service, numpy only.

**Testing consequence:** a trainee can read every line of the scoring maths.
When a retrieval test fails you can answer *why* — the term was out of
vocabulary, the synonym expansion missed, the chunk was too long — instead of
shrugging at a vector database. `SYNONYMS` exists because capital markets is
full of aliases (`CE`, `PE`, `OI`, `PCR`, `F&O`), and a retriever that does not
know them fails on perfectly reasonable questions. Six tests cover exactly that.

### Tools validate before they execute

Every tool in `app/agents/tools.py` carries a JSON Schema, a risk tier, and
explicit argument validation. `execute_tool` never raises: it returns a uniform
envelope with `ok`, `result`, and a typed `error.code` drawn from a closed set —
`missing_argument`, `type_error`, `out_of_range`, `invalid_argument`,
`unknown_symbol`, `unknown_tool`, `data_unavailable`, `internal_error`.

**Testing consequence:** tool contract testing is the part of this project that
maps most directly onto skills a manual tester already has. It is API testing —
boundary values, wrong types, missing fields, error codes — and 29 blue-team
cases plus 13 red-team cases live here. It is also the layer where an attack
either stops or does not: path traversal, SQL payloads and SSRF hosts are all
rejected at argument validation, before any handler runs.

### The agent loop is observable and bounded

`app/agents/single_agent.py` records every decision as a trace step, enforces a
step budget, and reports why it stopped: `completed`, `step_budget_exhausted`,
`input_blocked`, `llm_error`.

**Testing consequence:** "the agent looped forever" and "the agent picked the
wrong tool" are two of the most common real defects, and neither is visible from
the final answer alone. Because the loop publishes its reasoning, `tool_used`,
`tool_arg_equals`, `steps_max` and `stopped_reason` are all assertable. An agent
that does not expose this is an agent you cannot test — which is itself worth
writing up.

### MCP is the real protocol

`app/mcpsvc/protocol.py` implements JSON-RPC 2.0 over stdio with `initialize`,
`tools/list`, `tools/call` and `ping`. No third-party dependency, so the wire
format is readable. Each server is runnable standalone (`python -m
app.mcpsvc.risk_server`) and can be pointed at any MCP host.

Two client transports share one API: `InProcessMCPClient` (fast, for the suite)
and `StdioMCPClient` (real subprocess, real pipes).

**Testing consequence:** an integration that passes in-process can still fail
across a real transport — serialisation, timeouts, a server that dies mid-call.
Running the same suite both ways with `QTCAP_MCP_TRANSPORT=stdio` is how you
find that class of bug, and it costs one environment variable.

Note also that tool errors come back **in band** — as an `isError` result, not a
transport failure. A test asserting that distinction is testing something real:
a client that treats a validation error as a connection failure will retry
forever.

### Specialist boundaries are enforced in code

In `app/agents/orchestrator.py` each specialist declares the tools it owns, and
`Specialist.run` denies any call outside that set before it reaches a server.

**Testing consequence:** cross-agent privilege escalation is a genuine
multi-agent attack surface, and a boundary enforced only by a prompt is not
enforced at all. The `no_cross_agent_access` check asserts the denial is
recorded rather than silently tolerated.

### Guardrails are switchable

`app/guardrails/rules.py` holds thirteen controls, each with an id, a severity,
and an action (`allow`, `flag`, `sanitize`, `block`). `QTCAP_VULNERABLE_MODE=1`
downgrades every block to a flag.

IN-07 is the odd one out: it scans a document entering the corpus rather than a
question entering the pipeline, and its action is `flag` in every mode. A
document that cannot be loaded cannot be tested against, and the red-team labs
need to load exactly the documents this control objects to.

**Testing consequence:** this is the most important design decision in the
project for red-team training. Seven cases run with `vulnerable_mode: true` and
assert the attack *succeeds*, proving the controls are load-bearing. Without
that, a red-team suite is 121 green ticks that might equally be explained by a
model that was never going to comply anyway.

The controls are pattern-based, which is honest rather than ideal: three known
gaps are documented in the suites. Pattern matching catches the attacks it knows
and misses novel phrasing — a real property of real systems, and better taught
than hidden.

### Uploaded documents belong to a browser, not to the instance

`app/rag/corpus.py` keeps per-caller document overlays in memory, addressed by an
opaque id the console generates and sends as `X-QTCAP-Corpus`. A query carrying
no such header retrieves from the fifteen curated documents and nothing else.
`RAGPipeline.answer(corpus=...)` swaps the retriever for that caller's overlay
for the duration of one call; the shared `VectorStore` is never mutated.

**Testing consequence:** "whose data is in the index?" is the first question to
ask about any multi-tenant RAG system, and here the answer is enforced in code
and asserted in `tests/test_documents.py` rather than promised in a README. The
interesting cases are not the happy path — they are one student's document
staying out of another's retrieval, an upload not moving a shipped blue-team
result, and an uploaded passage staying distinguishable from a curated one all
the way into the prompt (`| UNVERIFIED USER UPLOAD`).

### The UI publishes state, not just prose

Every result region in `app/web` carries a `data-testid` and a derived state
attribute: `data-state` on answers, `data-source` on market provenance,
`data-ok` on tool calls, `data-specialist` and `data-status` on subtasks,
`data-stage` on trace steps.

**Testing consequence:** UI tests read the state the application derived, not
the sentence it generated. `assert state in ("answered", "sanitized")` is stable
across model changes; `assert "put-call parity is" in text` is not. When you
test a real AI product, ask the developers for these attributes — it is an
afternoon of their time and it is the difference between a UI suite that lives
and one that gets deleted.

---

## Request lifecycle

**RAG**

```
query → input guard → retrieve (hybrid, top-k) → build context
      → generate → attach citations → score grounding → output guard → answer
```
Each stage appends a trace entry. A failure is localised by reading the trace,
not by guessing.

**Single agent**

```
query → input guard → [plan → authorise tool → execute → observe]×N
      → synthesise → output guard → answer
```
The loop exits on a final answer or the step budget, and says which.

**Multi-agent**

```
query → input guard → decompose into subtasks → route each to one specialist
      → specialist calls its MCP server → collect findings
      → supervisor synthesises → output guard → answer
```
Failed subtasks are surfaced in the answer rather than dropped — itself a test
(`multi_agent_synthesis`).

---

## Configuration

Everything is environment-driven (`app/config.py`), so a trainee changes the
model, the data mode, the transport or the guardrail state without editing code.
See `.env.example` for the full list. The ones that change what you are testing:

| Variable | Effect |
|---|---|
| `QTCAP_LLM_PROVIDER` | `stub` \| `openai` \| `anthropic` \| `ollama` |
| `QTCAP_MARKET_MODE` | `auto` \| `live` \| `snapshot` |
| `QTCAP_MCP_TRANSPORT` | `in_process` \| `stdio` |
| `QTCAP_VULNERABLE_MODE` | `1` disables every guardrail |
| `QTCAP_AGENT_MAX_STEPS` | agent step budget |
| `QTCAP_RAG_TOP_K` | passages retrieved per query |

---

## What was deliberately left out

Being explicit about scope is part of a test strategy, so: there is no
authentication, no persistence, no rate limiting, no order placement, and no
real broker integration. The corpus is illustrative and the margin model is a
simplified proxy, not exchange SPAN.

None of these are oversights. Each is a boundary, and naming boundaries is how
you stop a test suite from sprawling into work nobody asked for — and how you
tell a stakeholder what your green pass rate does *not* cover.
