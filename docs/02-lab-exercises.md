# Lab Exercises

Thirteen graded exercises. The first four build confidence, the middle four are
the real work, and the last four are the ones worth putting in a portfolio.

Work in order. Each lab states what you produce and how to know you are done.

---

## Lab 1 — Exploratory testing with domain eyes
**Time: 45 min · Difficulty: ●○○○**

Run the app (`./run.sh`) and spend forty-five minutes trying to get a wrong
answer out of the RAG assistant, using only your capital-markets knowledge.

Target the things you know are easy to get wrong: lot sizes, which index expires
on which day, cash versus physical settlement, what happens to an in-the-money
stock option nobody squares off, the difference between SPAN and exposure
margin, STT on exercised versus sold options.

**Produce:** a table of ten observations — question, what it answered, what is
wrong or unsupported, and how bad it would be in production.

**Done when:** at least three observations are things a non-domain tester would
have read straight past.

---

## Lab 2 — Read the trace, localise the fault
**Time: 30 min · Difficulty: ●○○○**

For five of your Lab 1 observations, work out *which stage* went wrong by
reading the trace panel rather than guessing.

- `retrieval → empty` or a low top score — the corpus does not cover it, or the
  query wording missed. A retrieval problem.
- Good retrieval but low `grounding` — the model wrote something the passages do
  not support. A generation problem.
- `output_guard → sanitize` — a control modified the answer. A policy behaviour,
  not a bug.
- `input_guard → blocked` — the question never reached the pipeline at all.

**Produce:** each observation labelled `retrieval` / `generation` / `policy` /
`data`.

**Done when:** you can state, for each, which file you would open first.

---

## Lab 3 — Your first automated tests
**Time: 1 hour · Difficulty: ●●○○**

Turn Lab 1 into `tests/suites/blue/06-my-cases.yaml` — ten cases, ids `MY-001`
onward. Use [test-case-spec.md](test-case-spec.md).

```bash
python tools/run_suite.py blue --file tests/suites/blue/06-my-cases.yaml
```

Rules: at least two checks per case; no assertion on a live price; no assertion
on an exact generated sentence unless it is a refusal message.

**Done when:** every case either passes, or fails for a reason you can explain
in one sentence — and you have decided whether that reason is a product defect
or a test defect.

---

## Lab 4 — Exact tests on pure functions
**Time: 45 min · Difficulty: ●●○○**

`app/market/derivatives.py` is pure — same inputs, same outputs, forever. This
is the one place in an AI system where classical assertions work perfectly, so
it is the right place to build confidence.

Write ten `target: math` cases covering things you can verify independently:

- Put-call parity: `C − P = S − K·e^(−rT)` at any strike.
- An ATM call and put on the same strike have identical gamma and vega.
- A deep ITM call has delta approaching 1; a deep OTM put approaches 0.
- An option at expiry (`t: 0`) is worth exactly its intrinsic value.
- A long straddle's maximum loss equals the total premium paid.
- A naked short call's maximum loss is `unlimited`.
- An iron condor is a credit position with two breakevens.
- `implied_volatility` round-trips: price at 14%, solve, get 14% back.

Compute each expected value first (`python -c "from app.market.derivatives
import black_scholes; print(black_scholes(...))"`), then assert it with
`json_path_close_to`. Never guess a number into a test.

**Done when:** ten cases pass and you have found at least one invariant that
holds for every input — that is the pattern you will reuse everywhere.

---

## Lab 5 — Hunt seeded defects
**Time: 1.5 hours · Difficulty: ●●●○**

```bash
python tools/seed_defect.py --list
python tools/seed_defect.py D1
./test.sh fast
python tools/seed_defect.py --restore
```

Eight defects are available. **Five are caught by the shipped suite. Three are
not.** That is deliberate, and the three are the more valuable half of this lab.

| # | Defect | Caught? | What it costs in production |
|---|---|---|---|
| D1 | NIFTY lot size 75 → 50 | **yes** | every margin and contract value understated by a third |
| D2 | Gamma divided by strike, not spot | **yes** | hedge ratios drift silently on away-from-money options |
| D3 | Agent tool-authorisation check removed | **no** | the agent can invoke tools it was never granted |
| D4 | Advice control downgraded to flag | **yes** | recommendations reach retail users — compliance breach |
| D5 | Synthetic data labelled as live | **yes** | generated prices presented as real market data |
| D6 | Citations always empty | **yes** | no claim can be traced to a source |
| D7 | Cross-agent boundary removed | **no** | a specialist reaches another's MCP server |
| D8 | Retrieval synonym expansion disabled | **no** | trade abbreviations retrieve the wrong passages |

Run each one. For the five that are caught, note *which* cases fired and whether
the failure message would let a developer fix it without asking you a question.

For **D3, D7 and D8** the suite stays green — and a green suite over a real
defect is the most dangerous thing in testing. For each, answer:

1. Why does nothing catch it? (For D3 and D7: the deterministic backend never
   attempts a forbidden call, so the removed check is never exercised. For D8:
   ask the harder question — does the synonym map change *any* retrieval result
   at all? If not, is the feature inert, and is *that* the defect?)
2. What would a test that catches it look like?

**Produce:** three new test cases, one per undetected defect, that fail with the
defect injected and pass without it. Prove both directions.

**Done when:** `seed_defect.py D3` makes your new case fail, and `--restore`
makes it pass. Same for D7 and D8. This is the single most valuable exercise in
the project: you have just closed a coverage gap you found yourself.

---

## Lab 6 — Red team the agent
**Time: 2 hours · Difficulty: ●●●○**

Read `tests/suites/red/01-injection-jailbreak.yaml` — every case has a `notes`
field explaining its technique.

Then write fifteen of your own in `tests/suites/red/04-my-attacks.yaml`, drawing
on what you know about the domain rather than a generic jailbreak list. Cover at
least five families:

- Instruction override and persona reassignment.
- Extraction of the system prompt, tool schemas, or configuration.
- Soliciting advice through indirect framing ("my friend is asking", "purely
  hypothetically", "as my compliance officer would say").
- Market abuse wrapped in a professional pretext.
- PII smuggled into an otherwise legitimate question.
- Numerical integrity: false premises, "just estimate it", "skip the tool".

Verify every case in **both** modes:

```bash
python tools/run_suite.py red --file tests/suites/red/04-my-attacks.yaml
QTCAP_VULNERABLE_MODE=1 python tools/run_suite.py red --file tests/suites/red/04-my-attacks.yaml
```

If an attack is not blocked, do not weaken the test to make it green. Assert the
real behaviour, add a `# KNOWN GAP:` comment saying what a hardened build should
do, and raise it as a defect. Three such gaps already ship in the suite — find
and read them first.

**Done when:** fifteen cases pass, at least two are `vulnerable_mode: true`
proofs, and any gap you found is documented rather than hidden.

---

## Lab 7 — MCP and transport testing
**Time: 1 hour · Difficulty: ●●●○**

Talk to a server by hand, over a pipe:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"calc_margin","arguments":{"symbol":"NIFTY","lots":2}}}' \
 | python -m app.mcpsvc.risk_server
```

Then run the whole suite over real subprocess pipes instead of in-process:

```bash
QTCAP_MCP_TRANSPORT=stdio ./test.sh fast
```

Investigate:

1. Does anything behave differently across the two transports? Time them.
2. Send a malformed JSON line to a server. What comes back? Is it a
   JSON-RPC parse error, or does the process die?
3. Call a tool with bad arguments over MCP. Confirm the failure arrives
   **in band** (`isError`) rather than as a transport failure — a client that
   confuses the two will retry a validation error forever.
4. Kill a server mid-session and make a call. Is the error actionable?

**Produce:** five `target: mcp` cases covering protocol-level behaviour, not
just tool results.

---

## Lab 8 — UI automation
**Time: 1.5 hours · Difficulty: ●●●○**

```bash
python -m playwright install chromium
pytest tests/test_ui.py -v
```

Read `tests/test_ui.py` and notice that every assertion reads a **state
attribute** the UI derived, never generated prose.

Add five tests:

1. The market panel flags synthetic data distinctly from live data.
2. The RAG panel shows zero contexts for an out-of-corpus question.
3. The agent panel shows a failed tool call as failed (`data-ok="false"`).
4. Toggling vulnerable mode changes the header pill, and toggling back restores it.
5. The multi-agent panel shows at least two distinct specialists for a compound query.

**Done when:** all five pass twice in a row. Any test that passes only sometimes
is a test you must either fix or delete — a flaky suite trains people to ignore
red.

---

## Lab 9 — Model comparison
**Time: 2 hours · Difficulty: ●●●●**

Run the full suite against at least two backends:

```bash
./test.sh fast                                                   # stub baseline
QTCAP_LLM_PROVIDER=ollama QTCAP_LLM_MODEL=llama3.1:8b ./test.sh fast
QTCAP_LLM_PROVIDER=openai OPENAI_API_KEY=sk-... ./test.sh fast
```

Failures will appear. Sort every one into exactly one bucket:

- **Application defect** — the same fault exists on every backend.
- **Over-specified test** — asserts wording a different model phrases differently.
- **Legitimate model difference** — a different but equally valid tool choice.
- **Non-determinism** — run it ten times and count.

**Produce:** a comparison table — pass rate by suite and by severity per model,
with failures categorised, plus a recommendation on which model you would deploy
and what you would tighten first.

**Done when:** you can defend the recommendation to someone who will be paying
for the tokens.

---

## Lab 10 — Extend the check vocabulary
**Time: 1.5 hours · Difficulty: ●●●●**

Open `tests/runner/evaluators.py`. Adding a check is about twenty lines:

```python
@check("citation_precision")
def c_citation_precision(result, params):
    """Every cited document must actually appear among the retrieved contexts."""
    cited = {str(c).upper() for c in result.get("citations", []) or []}
    retrieved = {str(c.get("doc_id", "")).upper() for c in (result.get("contexts") or [])}
    invented = cited - retrieved
    return not invented, "all citations retrieved" if not invented else f"invented: {sorted(invented)}"
```

Implement three:

1. `citation_precision` — as above. Catches a model citing a document it never saw.
2. `numeric_consistency` — every number in the prose also appears in the tool
   output. Catches an agent that calls a tool and then writes a different figure.
3. `no_stale_without_warning` — a payload marked stale must carry a warning.

Then write cases that use them.

**Done when:** all three are used by at least one passing case, and you have
documented them in `test-case-spec.md`.

---

## Lab 11 — Build a fourth MCP server
**Time: 3 hours · Difficulty: ●●●●●**

Add a **portfolio** server with tools for position aggregation, portfolio-level
Greeks, and the margin benefit of a hedged position. Then add a
`portfolio_analyst` specialist that owns it.

Follow the pattern in `app/mcpsvc/risk_server.py` and
`app/agents/orchestrator.py`. Register routing rules so the supervisor sends
portfolio questions to it.

**Produce:** the server, the specialist, and fifteen tests — blue-team for
correct behaviour, red-team for the new attack surface you just created. Ask
yourself what a portfolio tool makes possible that was not possible before:
position data is more sensitive than market data, and a boundary that was
theoretical is now real.

**Done when:** the full suite still passes, your new tests pass, and
`no_cross_agent_access` still holds with four specialists.

---

## Lab 12 — The client report
**Time: 2 hours · Difficulty: ●●●●**

Produce the deliverable. One page of prose plus the HTML report.

```bash
./test.sh all
open reports/test-report.html
```

Structure:

1. **Scope** — what you tested and, explicitly, what you did not.
2. **Method** — the suites, the backends, the transports, how many runs.
3. **Results** — pass rate by severity. One critical failure outranks forty
   medium ones, and your summary should make that obvious at a glance.
4. **Findings** — each with an id, reproduction steps, and a business
   consequence. Write consequences, not symptoms: not "the agent ignores the
   position side", but "a short futures position is margined as long,
   understating the requirement by X on a Y-lot trade".
5. **Known gaps** — the controls that depend on phrasing, the schema that
   accepts unknown arguments, the defects your suite does not catch.
6. **Recommendation** — is this fit to put in front of retail users, and what
   are the three things you would fix first?

**Done when:** someone who has never seen the system could read your page and
make a go / no-go decision.

---

## Grading

| Level | Evidence |
|---|---|
| **Foundation** | Labs 1–4. Can test a RAG system by hand and write stable YAML cases. |
| **Practitioner** | Labs 5–8. Finds seeded defects, closes coverage gaps, red-teams an agent, automates a UI. |
| **Advanced** | Labs 9–12. Compares models with evidence, extends the framework, builds and secures a new agent, reports to a client. |

An honest "I could not catch D7, and here is why" is worth more than a green
suite that proves nothing. Say so in the report.


---

## Lab 13 — Test the multi-tenant boundary
**Time: 1 hour · Difficulty: ●●●●**

The hosted build serves a whole class from one URL. That creates a class of
defect a single-user app cannot have: one user changing what another user sees.

Open two browser windows against the same instance, ideally as two students.

1. In window A, untick **guardrails** and send an injection. It succeeds.
2. In window B, with guardrails on, send the same injection. It must still be
   refused. If it is not, window A just disabled window B's safety controls.
3. In window A, set a Groq key. In window B, check the header pill still shows
   `stub`. A key must never leak across sessions.
4. File a finding in window A. Confirm it appears in window B's Findings list —
   findings are deliberately shared, unlike keys and guardrail state. Ask
   yourself which of those three behaviours you would want in a real product.
5. Hit the rate limit deliberately (the agent panel, repeatedly). Confirm you get
   a 429 with an actionable message rather than a hang or a stack trace.

**Produce:** five cases covering isolation. Two of them cannot be written as YAML
against a single process — say so, and describe the harness you would need.

**Done when:** you can state, for each piece of state in the app (model choice,
key, guardrail mode, findings, market snapshots), whether it is per request, per
browser, or shared — and whether that is the right answer.
