# Capital Markets Agentic Capstone

A complete, runnable training project that takes a **manual tester with capital-markets
domain knowledge** and turns them into a **tester of RAG and agentic AI systems**.

Three applications, one live market-data layer, one knowledge corpus, and **586 tests, plus a 377-case IEEE 829 workbook**
— 206 blue-team, 121 red-team, 54 UI, 37 hosting-security, 30 document-corpus, 30 IEEE harness, 51 test-lab, 26
storage, 31 design-system — all green. The IEEE workbook is separate, and deliberately is not.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Web console  ·  RAG │ Single Agent │ Multi-Agent │ Tools │ Data │ ⚙  │
└──────────────────────────────────────────────────────────────────────┘
        │                    │                        │
   ┌────▼─────┐        ┌─────▼──────┐         ┌───────▼────────┐
   │   RAG    │        │  Single    │         │  Supervisor    │
   │ pipeline │        │   agent    │         │  + 3 specialists│
   └────┬─────┘        └─────┬──────┘         └───────┬────────┘
        │                    │                 MCP (JSON-RPC 2.0/stdio)
        │                    │              ┌─────────┼─────────┐
        │                    │         market_data   risk   research
        └────────────┬───────┴────────────────┴────────┴─────────┘
                     │
        ┌────────────▼──────────────┐   ┌──────────────────────┐
        │ Guardrails (13 controls)  │   │ Live market data     │
        │ in / out, toggleable      │   │ live→snapshot→synth  │
        └───────────────────────────┘   └──────────────────────┘
```

## Bring your own free key

The app runs with **no API key at all** on a deterministic offline stub. To use a real
model, open **⚙ Model & key** in the console and paste a free key — Groq is the quickest
to obtain. Your key is kept in your browser, sent with each request, used once, and
**never stored on the server**.

Supported: **Groq**, **Cerebras**, **Google AI Studio (Gemini)**, **OpenRouter**
(`:free` models), Mistral, Together, xAI/Grok, OpenAI, Anthropic, and **Ollama** for
local runs. Ollama only works when the app runs on your own machine — a hosted instance
cannot reach your laptop's localhost.

## Deploy it free for a class

**Hugging Face Spaces** is the recommended shared URL — no card, no trial clock.
Docker is the cleanest SDK but is gated on HF (it shows as "Paid" when you are
signed out or it is not enabled on your account), so the project also ships a
**Gradio SDK** entry point, which is free to everyone and serves the identical
FastAPI console:

```bash
./tools/prepare_space.sh gradio ../qtcap-space   # free on any account
./tools/prepare_space.sh docker ../qtcap-space   # if Docker is enabled for you
```

Need a URL for one class today, with no hosting account at all? Open
[`tools/run_in_colab.ipynb`](tools/run_in_colab.ipynb) in Google Colab: it
installs, runs a sanity check, and opens a public tunnel that needs no signup.

Serving it from **your own subdomain** (`capstone.yourdomain.com` rather than the
platform's hostname) is one CNAME record and no code change; `render.yaml` has
the block to uncomment, and `QTCAP_CANONICAL_HOST` redirects the old URL so a
class has exactly one address. Pair either with **GitHub Codespaces** so each
student gets the terminal the labs need. See [docs/04-deployment.md](docs/04-deployment.md) for the full comparison,
the security model behind bring-your-own-key, and what changes on a shared
instance.

```bash
docker build -t qtcap . && docker run -p 7860:7860 -e QTCAP_PUBLIC_MODE=1 qtcap
```

## Quick start

```bash
pip install -r requirements-dev.txt   # or requirements.txt to run without the tests
./run.sh                                  # http://127.0.0.1:8000
./test.sh fast                            # 327 cases in ~40 seconds
```

No API key is required. The default model backend is a deterministic offline stub,
which is what makes a 300-case regression suite reproducible. Switch to a real model
whenever you want:

```bash
export QTCAP_LLM_PROVIDER=openai    && export OPENAI_API_KEY=sk-...      # cloud
export QTCAP_LLM_PROVIDER=anthropic && export ANTHROPIC_API_KEY=sk-ant-... # cloud
export QTCAP_LLM_PROVIDER=ollama    && export QTCAP_LLM_MODEL=llama3.1:8b  # local
```

## The three applications

**1 — RAG assistant.** Answers questions about Indian equity derivatives strictly from a
15-document, ~43,000-word corpus. Returns citations, a grounding score, the retrieved
passages, and a stage-by-stage trace. Teaches: retrieval correctness, groundedness,
citation discipline, out-of-corpus refusal.

Trainees can **add their own documents** from the console — markdown, text, CSV, JSON
or HTML — and ask questions against them. An upload belongs to the browser that made
it: it is held in memory under an opaque per-browser corpus id, never written to disk,
and never visible to anyone else using the same instance. Every uploaded document is
scanned by the IN-07 document guard on the way in and its findings are shown in the
list; a poisoned document is **flagged, not blocked**, because a file you cannot load
is a file you cannot test against. Retrieved passages from an upload are labelled
`user-upload` in the evidence panel, in the trace, and inside the prompt itself.

**2 — Single tool-calling agent.** Eleven tools covering live quotes, option chains,
futures, FX, Black-Scholes pricing, Greeks, implied volatility, margin, payoffs and
knowledge search. Teaches: tool selection, argument extraction, step budgets,
error recovery, termination.

**3 — MCP multi-agent system.** A supervisor decomposes a request and delegates to three
specialists, each bound to its own MCP server over real JSON-RPC 2.0. Cross-agent tool
access is denied in code. Teaches: decomposition, routing, boundary enforcement, and
whether a specialist's finding actually survives into the final answer.

## Market data

Live public APIs, no keys: Yahoo Finance (quotes, OHLC), NSE India (option chains),
Frankfurter/ECB (FX), Stooq (index fallback). Futures are derived from live spot via
cost of carry.

Every payload declares its provenance — `live`, `snapshot`, or `synthetic` — and whether
it is stale. When a live call fails the system serves a recorded snapshot; with no
snapshot it generates clearly-labelled synthetic data and says so. **Tests assert on
provenance and structure, never on price levels**, which is why the suite is stable
whether the market is open, closed, or unreachable.

```bash
python tools/fetch_live_data.py          # refresh snapshots before a session
python tools/fetch_live_data.py --check  # connectivity check only
```

## The test suites

| Suite | Cases | What it asserts |
|---|---|---|
| Blue — RAG retrieval | 40 | right document retrieved and cited, grounding thresholds, out-of-corpus refusal, synonym handling |
| Blue — math & tool contracts | 40 | Black-Scholes values, put-call parity, Greek invariants, strategy payoffs, margin arithmetic, every tool error code |
| Blue — single agent | 40 | tool selection and negative selection, argument extraction, step budgets, error recovery |
| Blue — MCP & multi-agent | 40 | server routing, in-band protocol errors, decomposition, specialist routing, boundary enforcement |
| Blue — data & compliance | 46 | provenance, contract master, guardrail false positives, scope, PII handling, disclaimers |
| Red — injection & jailbreak | 47 | instruction override, persona attacks, prompt extraction, privilege escalation, obfuscation |
| Red — leakage & tool abuse | 41 | PII redaction, credential exfiltration, path traversal, SSRF, SQL, resource exhaustion, context poisoning |
| Red — financial harm | 33 | investment advice, guaranteed returns, market-abuse facilitation, hallucination, numerical integrity |
| UI (Playwright) | 49 | every panel, trace rendering, refusal display, validation errors, per-request guardrail switch, key handling, runner, findings |
| Hosting security (pytest) | 37 | key redaction, SSRF allowlist, per-request isolation, rate limiting, findings redaction, custom-domain host policy, per-browser document isolation |
| Documents (pytest) | 30 | corpus isolation, provenance labelling, poisoned-document detection, format handling, upload limits |
| Test lab (pytest) | 47 | accounts and passcode hashing, session forgery, per-user isolation, defect publishing, no key ever stored |
| IEEE harness (pytest) | 30 | every workbook row bound, oracles independent of the app, RAGAS proxies directional |
| IEEE 829 workbook | 377 | the full manual suite, executed and written back into the spreadsheet — see below |

```bash
./test.sh fast       # YAML runner, plain output, fastest
./test.sh all        # pytest + HTML report in reports/
./test.sh red        # red team only
./test.sh ui         # browser tests
python tools/run_suite.py blue --category tool_selection
python tools/run_suite.py --id BLUE-RAG-001
QTCAP_MCP_TRANSPORT=stdio ./test.sh fast     # same suite over real pipes
```

Tests are **YAML, not Python** — a manual tester adds one without writing code:

```yaml
- id: MY-001
  title: A conceptual Greeks question goes to the knowledge base, not the calculator
  category: tool_selection
  severity: high
  target: agent
  input: {query: "Explain what gamma means"}
  checks:
    - {type: tool_used, any_of: [search_knowledge_base]}
    - {type: tool_not_used, any_of: [calc_greeks]}
    - {type: steps_max, value: 3}
```

50+ check types are documented in [docs/test-case-spec.md](docs/test-case-spec.md).

## Guardrails, and proving they matter

Thirteen controls — seven on input (injection, jailbreak, extraction, tool abuse, PII,
scope, and IN-07 for documents entering the corpus) and six on output (PII, secrets,
advice, predictions, disclaimers, market abuse).

All of them can be switched off:

```bash
QTCAP_VULNERABLE_MODE=1 ./run.sh
```

Seven red-team cases run in this mode and assert the attack **succeeds**. A control you
have never watched fail is a control nobody should trust, and a red-team suite that has
only ever seen green is not evidence of anything.

Three **known gaps** are documented in the suites rather than hidden: keyword-based scope
classification, narrow resource-exhaustion patterns, and tool schemas that ignore unknown
arguments. Each is written as a passing test asserting real behaviour, with a
`# KNOWN GAP:` comment saying what a hardened build should do.

## Adding your own documents

```bash
# from the console: RAG Assistant -> Knowledge base -> drop files
# or over the API, with your own corpus id:
curl -X POST localhost:8000/api/rag/documents \
     -H 'Content-Type: application/json' -H 'X-QTCAP-Corpus: my-browser' \
     -d '{"filename":"desk-notes.md","content":"## Lot policy\n\nFour lots overnight, no more."}'
curl localhost:8000/api/rag/documents -H 'X-QTCAP-Corpus: my-browser'
```

Ten documents per corpus, 200KB each, held in memory with a six-hour idle
expiry. The shipped suites run **without** a corpus header, so an upload can
never move a blue-team result — which is itself asserted in
`tests/test_documents.py`.

To add a document to the **curated** corpus for everyone — the trainer's job,
not a trainee's — drop a markdown file into `knowledge_base/` with `doc_id`,
`title`, `category` and `authority` front matter and restart. That path is
deliberately a file on disk and a restart, because changing what a whole class
retrieves should be a deployment, not a click.

## Documentation

| Document | For |
|---|---|
| [Trainee handbook](docs/00-trainee-handbook.md) | **Start here** — ten steps from first run to final report |
| [Architecture](docs/01-architecture.md) | How the pieces fit, and why each one is built to be testable |
| [Lab exercises](docs/02-lab-exercises.md) | Fourteen graded exercises with seeded defects |
| [Test case spec](docs/test-case-spec.md) | Complete YAML format and check vocabulary |
| [Facilitator guide](docs/03-facilitator-guide.md) | Running this as a five-day course |
| [Deployment](docs/04-deployment.md) | Free hosting, bring-your-own-key, and what changes on a shared instance |
| [IEEE 829 suite](docs/05-ieee-suite.md) | Executing the 377-case workbook and reading its failures |
| [Test Lab](docs/06-test-lab.md) | Google sign-in, the three dashboards, defects and the shared board |

## The Test Lab

The whole 377-case suite is published **inside the console**. A trainee signs in
with Google, runs cases against the three applications, marks their own verdict,
raises defects and publishes the ones worth sharing to a board the class can
read.

- **Sign in from the header on any page.** Google when an instance is configured
  for it, and an email-and-passcode account on every instance — so a deployment
  with no Google client id is still fully usable. Passcodes are hashed with
  PBKDF2 and never stored in the clear; the address is not verified, which the
  docs say plainly rather than implying otherwise.
- **My Account** — execution history, defects, coverage, and markdown/CSV report
  downloads.
- **Three dashboards** — RAG, single agent, multi-agent — each showing what that
  trainee has executed, split pass / fail / capability gap / blocked.
- **Results are private** to the account that produced them. Defects start
  private and are published deliberately; the public board carries the author's
  name and never their email address.
- **The model key stays in the browser.** Signing in says whose results these
  are; it does not give the server custody of anybody's credentials. There is a
  test asserting no key reaches storage.
- **A tester may overrule the harness.** The automated status and the tester's
  verdict are separate fields, because an automated check is evidence and a
  verdict is a judgement.
- **Summary report** as markdown, including the list facilitators should read
  first: failing cases with no defect raised against them.

Sign-in needs one public Google client id and no client secret — see
[docs/06-test-lab.md](docs/06-test-lab.md). Without one, a local-only sign-in
keeps the lab usable offline, and it is refused outright when
`QTCAP_PUBLIC_MODE=1`.

Accounts, results and defects live in SQLite on a laptop and in PostgreSQL when
`DATABASE_URL` is set — same code, same schema, both backends covered by the
same tests.

> **Set `DATABASE_URL` before a class uses the hosted instance.** A free web
> service has no persistent disk, so without it a redeploy deletes every
> account, result and defect. A Neon free database is permanent and needs no
> card: [docs/07-database.md](docs/07-database.md).

## The IEEE 829 workbook

`tests/ieee/Capital_Markets_GenAI_Agent_Test_Suite_IEEE.xlsx` holds 377 manual
test cases in IEEE 829 form — 209 for a GenAI copilot, 168 for a trading agent,
across 32 requirement areas from RAGAS metrics to human-in-the-loop approval
gates and derivatives trading guardrails. Every row is executable:

```bash
python tools/run_ieee_suite.py                    # all 377, about a minute
python tools/run_ieee_suite.py --category G06     # one category
python tools/run_ieee_suite.py --id TC_G_G04_046  # one case
```

The run writes **Status**, **Actual Result**, **Defects** and **Remarks** back
into every row of a copy of the sheet, and adds four sheets: an **Execution
Summary**, a **Defect Register**, and a **RAG Applicable** / **Agent
Applicable** pair that re-cut every case by which application it actually
exercises — the view a tester handed one pipeline needs, which the workbook's
requirement-area layout does not give them.

**It does not all pass, on purpose.** A representative run:

| Verdict | Cases | |
|---|---|---|
| Pass | 219 | the expected result was observed |
| Fail | 66 | a real defect, with the evidence attached |
| Fail (expected) | 85 | a requirement this system has no implementation for |
| Blocked | 7 | a live market feed was unreachable — not a pass |

Split by application: **RAG 210 cases, 71% pass**; **Agent 199 cases, 46% pass**.
The gap between those two numbers is the finding — the retrieval pipeline is
largely built, the agent's operational half largely is not.

Eighteen distinct defects sit behind those failures, each named in the Defect
Register with the cases that prove it. The financial answer key
(`tests/ieee/oracles.py`) is implemented from first principles and imports
nothing from `app/`, and the twelve RAGAS metrics are deterministic lexical
proxies rather than LLM judgements — both choices are explained in
[docs/05-ieee-suite.md](docs/05-ieee-suite.md).

## Seeded defects

Eight defects can be injected on demand so trainees can prove the suite catches them —
and, for three of them, discover that it does not:

```bash
python tools/seed_defect.py --list
python tools/seed_defect.py D1     # wrong NIFTY lot size
./test.sh fast                     # which cases fire?
python tools/seed_defect.py --restore
```

Five are caught by the shipped suite. Three (agent tool authorisation, the cross-agent
boundary, retrieval synonym expansion) are not — closing those gaps is Lab 5, and it is
the most valuable exercise in the project.

## Requirements

Python 3.11+. Everything else is in `requirements.txt`. Playwright (for UI tests) needs
`python -m playwright install chromium` once. No database, no Docker, no API key.

---

*Quality Thought training project. Every market figure produced by this application is
educational and is not investment advice. Contract specifications, margin percentages and
tax rates are illustrative — verify against the current exchange and SEBI circulars before
relying on them.*
