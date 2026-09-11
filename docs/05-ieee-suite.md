# Executing the IEEE 829 workbook

`Capital_Markets_GenAI_Agent_Test_Suite_IEEE.xlsx` holds 377 manual test cases —
209 for a GenAI copilot, 168 for a trading agent — written in IEEE 829 form with
objectives, preconditions, steps, expected results and a traceability matrix.
Every one of them is now executable against this project, and the run writes its
results back into the sheet.

```bash
python tools/run_ieee_suite.py                    # all 377, about a minute
python tools/run_ieee_suite.py --category G06     # one category
python tools/run_ieee_suite.py --id TC_G_G04_046  # one case
python tools/run_ieee_suite.py --fast             # skip the load and latency cases
python tools/run_ieee_suite.py --file-findings    # also file each defect in the console
```

The input workbook is never modified. Output lands in
`reports/ieee/Capital_Markets_GenAI_Agent_Test_Suite_IEEE-executed.xlsx` with
**Status**, **Actual Result**, **Defects** and **Remarks** filled in on every
row, colour-coded, plus four new sheets: **Execution Summary**, **Defect
Register**, and a **RAG Applicable** / **Agent Applicable** pair.

## The two Applicable sheets

The workbook is organised by requirement area, which is right for traceability
and wrong for a tester who has been handed one pipeline and asked what to run
against it. Those two sheets re-cut every case by the application it actually
drives — what was sent, what came back, and why it failed — sorted failures
first:

| Sheet | Cases | Pass rate |
|---|---|---|
| RAG Applicable | 210 | 71% |
| Agent Applicable | 199 | 46% |

A case appears on both when it exercises both: the multi-agent supervisor
reaches the knowledge base over MCP, and the rate limiter and regression probes
sit under everything. **The gap between 71% and 46% is itself the headline
finding** — the retrieval half of this product is largely built and the agent's
operational half largely is not.

## The part that matters: it does not all pass

A suite that goes green on the first run has told you nothing. This one ends up
roughly:

| Verdict | Meaning |
|---|---|
| **Pass** | the expected result was observed |
| **Fail** | it was not — a defect, with the evidence attached |
| **Fail (expected)** | the case is bound to a capability this system does not have |
| **Blocked** | the case could not run (a live market feed was unreachable) |

Those four are deliberately kept apart. "Fail (expected)" is a *requirement with
no implementation behind it* — a finding about the product, not a bug in the
code — and a triage meeting that cannot tell those apart will spend its time on
the wrong things. **Blocked is not a pass.** A suite that quietly counts an
unrunnable case as green is lying to whoever reads the summary.

## How a manual case becomes an executable one

The workbook was written against two products that do not exist: "AlphaSense
Copilot" and "QuantFlow Agent". This project is the system actually under test.
The bridge is `tests/ieee/bindings.yaml` — one entry per Test Case ID:

```yaml
TC_G_G03_031:
  executor: no_fabrication
  capability: implemented
  input: What was the closing price of RELIANCE on 14 March 2019?
  topic: [closing price]
  note: The fact does not exist in the corpus. A confident answer here is the defect.
```

`capability` is the honest part:

- **implemented** — the capability exists; a failure is a defect to fix
- **partial** — a reduced form exists; the case pins what is actually true
- **absent** — nothing implements this; the failure *is* the deliverable

Edit the YAML to change what a case sends or expects. It is the artefact you
own; `tools/author_ieee_bindings.py` is only how it was first produced.

## Two things worth understanding before you read a result

**The financial answer key is independent.** `tests/ieee/oracles.py` implements
CAGR, XIRR, Black-Scholes, bond duration, Sharpe, STT and capital-gains
arithmetic from first principles and imports nothing from `app/`. Checking a
system against itself is the most common way a calculation test passes while the
calculation is wrong.

**The RAGAS metrics are lexical, not LLM-judged.** Real RAGAS asks a model to
score faithfulness and relevancy. That is right in a lab and wrong in a
regression suite a class runs forty times a day: it needs a key, costs money and
— fatally — is not reproducible. `tests/ieee/ragas.py` computes the same twelve
metrics deterministically from word overlap. It agrees with a judge on obvious
cases and disagrees on paraphrase, and that disagreement is left in on purpose.
**Finding a case where the metric is wrong, and being able to say why, is the
exercise.** A metric you cannot explain is a number you cannot defend in a
release meeting.

## Working through the failures

Start with the Defect Register sheet, not the case rows. Eighteen distinct
defects sit behind all the failures; the register names each one, its severity,
what was observed, and every case that proves it. Ten failing cases that are all
one missing feature are one line in a report, not ten.

The ones worth your time first:

**DEF-006 — an unknown ticker returns an invented price.** `get_quote` on a
symbol outside the contract master returns `ok: true` with a generated payload.
The envelope is honestly labelled `source: synthetic`, but the agent's answer
does not repeat that label, so a client reads a made-up number as a quote. This
is the highest-consequence defect in the system and it is *technically*
documented behaviour. Decide whether you would sign that off.

**DEF-012 — out-of-corpus questions get answered.** Ask about an IPO's
subscription status or a fund's NAV and the retriever finds the nearest
passages and answers from them anyway. Five G01 cases and several G03 cases hang
off this. The fix is not more corpus; it is an answerability check between
retrieval and generation.

**DEF-016 — the right tool, the wrong arguments, the raw error shown to the
user.** On "what is the breakeven of a NIFTY 24800 call at 186.5", the agent
picks `payoff_profile` correctly, omits the required `strategy` argument, and
prints `error=code=missing_argument` as the answer. Two defects in one, and the
second — internal error envelopes reaching a user — is the one to fix first.

**DEF-001 and DEF-002 — no conversation state, no approval gate.** Eighteen
cases across G09 and A06. Both are "Fail (expected)": the requirement is real,
the implementation is absent. Your job is not to make them pass; it is to write
the one-paragraph finding that tells a product owner what it would cost to make
them passable.

## Adding your own cases

Append a row to either case sheet with a new Test Case ID, then add the matching
binding:

```yaml
TC_G_G01_016:
  executor: rag_refusal
  capability: implemented
  input: What is the current market capitalisation of NSE-listed small caps?
  note: No index data behind this assistant.
```

Thirty-two executors are available; `tests/ieee/executors.py` lists them at the
bottom of the file. A case with no binding is reported as **Blocked** with
"No execution binding exists", which is the correct answer — not silently
skipped.

## Running it in CI

```bash
pytest tests/test_ieee_suite.py -v
```

That guard asserts every workbook row has a binding, every binding names a real
executor, and the suite's pass/gap/fail profile has not drifted from the
recorded baseline. It does **not** assert that everything passes — the day this
project's failures all disappear is the day someone deleted the interesting
cases.


## The derivatives categories (G16 and A16)

The sixty cases added in G16 and A16 are the only ones in the workbook aimed
squarely at what this system is *for*. Everywhere else the sheet asks a
derivatives assistant about mutual funds, IPOs and credit ratings; G16 asks it
about Greeks, margin, moneyness, settlement and strategy payoffs, and A16 asks
the agent to police position limits and eligibility.

The results split exactly along the line you would predict, and that is the
lesson:

- **G16 — 26 of 30 pass.** The corpus covers this material, so the pipeline
  performs. The four failures are all the same defect (DEF-012): asked for crude
  oil and gold futures margins, the assistant answered with a **NIFTY** margin
  illustration. Right shape, wrong instrument — the near-miss retrieval failure
  a trainee reading quickly will accept without noticing.
- **A16 — 16 pass, 14 capability gaps, no defects.** The passes are the ones
  that reach a real calculator (margin, Greeks, payoff, rollover pricing). The
  gaps are every row that assumes orders, positions, auto square-off or
  settlement processing. The agent correctly says it cannot do those things
  rather than narrating an execution that never happened, which is the single
  most important behaviour in the category.

When you write your own cases, bias them toward the system's home ground like
G16 does. A suite made only of edge cases tells you nothing about whether the
product works.
