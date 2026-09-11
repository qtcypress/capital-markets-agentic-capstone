# Facilitator Guide

A five-day delivery plan for this capstone, plus the things that go wrong when
running it with a live batch.

## Before the batch

**A week out.** Have every trainee install Python 3.11+, clone the project, run
`pip install -r requirements.txt`, and confirm `./test.sh fast` reports
327 passed. Doing this on day one wastes a morning.

**The morning of day one.** Run `python tools/fetch_live_data.py` on a machine
with normal internet access, during market hours, and distribute the resulting
`data/snapshots/*.json`. Every trainee then works against identical data, and
the live-API path stays demonstrable even from a network that blocks NSE.

**Note on NSE.** It blocks datacentre IPs and rate-limits aggressively. On
corporate or cloud networks the option-chain fetch will fail. This is not a
defect to fix during the session — it is the exact reason the provenance model
exists, and it makes a better teaching moment than a working fetch would.

## Five-day plan

| Day | Focus | Labs | Outcome |
|---|---|---|---|
| 1 | Orientation, RAG concepts, exploratory testing | 1, 2 | Each trainee has ten domain-informed observations and can localise a fault from the trace |
| 2 | YAML cases, pure-function testing, tool contracts | 3, 4 | Twenty of their own cases running green |
| 3 | Agents, tool selection, MCP, seeded defects | 5, 7 | Found five defects; closed at least one coverage gap themselves |
| 4 | Red teaming and UI automation | 6, 8 | Fifteen attack cases plus five UI tests |
| 5 | Model comparison and reporting | 9, 12 | A client-ready report |

Labs 10 and 11 are for trainees who finish early, or a second week.

## Session-by-session notes

**The idea that does the most work** is the one in Lab 4: for a value you cannot
predict, assert an invariant. Trainees arrive expecting to assert equality and
leave knowing why they cannot. Spend real time here — a call delta is always in
[0,1] whatever the market does; a naked short call is always unlimited loss; the
lot size is always 75. Once that lands, the rest of the course follows.

**The moment that changes minds** is the vulnerable-mode toggle in Lab 6. Run it
live at the front of the room: ask the injection in hardened mode, watch the
refusal, flip the switch, ask again. Until a tester has watched a guardrail fail,
"the guardrails work" is something they believe rather than something they know.

**The most common wrong instinct** is asserting on generated sentences. It will
pass on the day it is written and fail the following week. Catch it early: when
you see `contains: "Put-call parity is the relationship that"` in a review, ask
what the test is really trying to prove, and rewrite it together.

**The most common good instinct**, in this cohort specifically, is domain
suspicion — "that margin number looks wrong". Encourage them to chase it. A
tester who checks a figure against the contract master finds defects that no
amount of framework knowledge would surface.

## Assessment

Weight the report (Lab 12) most heavily, then the self-found coverage gaps
(Lab 5), then volume of passing cases. A trainee who documents an honest gap in
their own suite has understood more than one who submits 40 green cases that
assert nothing difficult.

A defensible submission contains: 20+ blue cases, 15+ red cases, 5 UI tests,
three closed coverage gaps, a model comparison table, and a one-page report with
a go / no-go recommendation.

## Reset between batches

```bash
python tools/seed_defect.py --restore
find . -name "*.orig" -delete
git checkout -- .          # if distributed as a repo
rm -rf reports/*.json reports/*.html
```

Confirm with `./test.sh fast` — 327 passed means the project is clean.

## Adapting the domain

The structure transfers. Replace `knowledge_base/`, the symbol and contract
tables in `app/market/sources.py`, and the domain terms in
`app/guardrails/rules.py`, and the same architecture teaches insurance claims,
healthcare coding, or banking operations. The three-application progression —
RAG, then agent, then multi-agent — is what carries the teaching load, not the
subject matter.
