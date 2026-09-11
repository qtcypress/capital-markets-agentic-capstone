# The Test Lab

The 377-case IEEE suite is published inside the console. A trainee signs in with
their Google account, runs cases against the three applications, marks their own
verdict, raises defects, and publishes the ones worth sharing to a board the
whole class can read.

Open **Test Lab** in the console. Nothing below needs a terminal.

## What belongs to whom

| Thing | Scope |
|---|---|
| The 377 published cases | everyone, readable signed out |
| Execution results | the signed-in trainee, nobody else |
| The tester's verdicts | the signed-in trainee |
| Defects | private to their author until published |
| The published board | everyone, readable signed out |
| **The model API key** | **the browser. Never sent anywhere but this app's own API, never stored** |

That last row is the one to read twice. Signing in says *whose* results these
are. It does not give this server custody of anyone's credentials. A training
instance that collected forty API keys into a database on a free tier would be
the most dangerous artefact in the project — so it doesn't. The key still lives
in `localStorage`, still rides on each request as a header, and is still used
once and discarded, exactly as it did before sign-in existed.

## Setting up Google sign-in

Sign-in needs one public client id. There is no client secret, because the
browser uses Google's ID-token flow and the server verifies the token with
Google directly.

1. Go to **console.cloud.google.com → APIs & Services → Credentials**.
2. **Create credentials → OAuth client ID → Web application**.
3. Under **Authorised JavaScript origins**, add the exact origin the class will
   use — `https://capitalmarket.genaitesting.online`. Add
   `http://localhost:8000` too if you want sign-in while developing. No redirect
   URI is needed.
4. Copy the client id and set it on the service:

```
QTCAP_GOOGLE_CLIENT_ID = 1234567890-abcdefg.apps.googleusercontent.com
QTCAP_SESSION_SECRET   = <a long random string>
```

`QTCAP_SESSION_SECRET` signs the session cookie. Unset, one is generated per
process, which means every redeploy signs the class out — noisy but never
insecure, and better than a default that ships in a public repository.

Optionally restrict who can sign in:

```
QTCAP_ALLOWED_EMAIL_DOMAINS = qualitythought.in
```

Leave it unset and any verified Google account works, which is usually what a
public training instance wants.

### Running without Google

On a laptop with no client id configured, the lab offers an offline sign-in: a
name, no password, a session. It exists so the app is usable and testable
offline. **It is refused outright when `QTCAP_PUBLIC_MODE=1`**, and there is a
test asserting that, because a development bypass that survives into production
is how authentication ends up decorative.

## The three dashboards

One card per application — RAG assistant, single agent, multi-agent — each
showing what *you* have executed, split into pass / fail / capability gap /
blocked. The suite tabs below filter the case list to the same three.

The split matters more than the totals. A trainee who has run 40 RAG cases and
2 agent cases has not tested this product; they have tested a quarter of it, and
the dashboard says so at a glance.

## Running, marking, and disagreeing

**Run** executes the case against the live system and stores the result against
your account. Up to 40 cases at a time — tick the boxes and use **Run selected**.
Load and latency cases are disabled here on purpose and say so; they belong in
`tools/run_ieee_suite.py` on a machine that isn't serving a class.

Then **mark your own verdict**: pass, fail or blocked. This is deliberately
separate from the harness's status, and you are allowed to disagree with it. An
automated check is *evidence*; the verdict is a judgement a person makes. Three
situations where you should overrule it:

- the case passed but the answer is wrong in a way the assertion didn't look at
- the case failed on a technicality that doesn't matter for this release
- the case is marked a capability gap and you think the requirement should be
  descoped rather than built

A suite where every verdict agrees with the machine is a suite nobody read.

## Defects

**Raise defect** from a result pre-fills the title, the steps, the expected
result from the workbook and the actual output from the run. Severity defaults
to high for a real failure and medium for a capability gap — change it if you
disagree.

A defect is **private until you publish it**. Publishing puts it on the shared
board with your name attached but never your email address; the board is a
shared artefact, not a mailing list. You can withdraw your own at any time. You
cannot touch anyone else's — not publish, not edit, not delete — and that is
enforced in code and asserted in `tests/test_lab.py` rather than promised here.

Anything credential-shaped pasted into a defect is redacted before storage, the
same filter the findings store uses.

## The summary report

**Download report** produces a markdown file: execution counts per suite, every
defect you raised with its steps and evidence, and — the part facilitators
should look at first — **failing cases with no defect raised against them**. A
run with twenty failures and two defects means eighteen findings died in
somebody's browser tab.

## Where the data lives, and when it disappears

SQLite, at `QTCAP_DB_PATH` (default `data/lab.sqlite3`).

**On a free hosting tier the disk is ephemeral.** A redeploy or a spin-down
takes the file with it, and everyone's results and defects go too. That is a
property of the hosting rather than a bug here, and the honest response is to
say so and give people an export button — which is what the report is for. Tell
a class to download their report before they leave.

If you have a persistent disk, point `QTCAP_DB_PATH` at it and the problem goes
away.

## A session that works

1. Facilitator sets the client id, shares the URL.
2. Trainees sign in, open **Model & key**, paste their own free Groq key.
3. Each takes one application — RAG, agent, multi-agent — and works their
   dashboard down, marking verdicts as they go.
4. Every failure either becomes a defect or gets a one-line note saying why not.
5. Publish the defects worth discussing. The board becomes the triage agenda.
6. Everyone downloads their report before the room empties.
