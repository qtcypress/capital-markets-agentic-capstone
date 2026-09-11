# Deployment

How to put this in front of a batch of students, for nothing, with each of them
using their own free API key.

> **Free tiers change.** The terms below are what I understood them to be when
> this was written, and I could not reach the providers' pages to re-check.
> Confirm the current limits on each platform's own pricing page before you
> commit a class to one. Nothing in the code depends on these details — the
> provider list is a table in `app/llm/registry.py` and the host is a Dockerfile.

---

## Hugging Face: checked, and it no longer fits

This was the original recommendation. Checking it against a real free account in
September 2026 showed otherwise, so here is what is actually true:

- **Docker SDK is PRO-only.** It shows a padlock and a "Paid" badge on
  `huggingface.co/new-space` *even when signed in*. Being signed out is not the
  explanation.
- **CPU Basic is PRO-only too.** Selecting it surfaces the tooltip: *"On the free
  tier, Gradio Spaces run on ZeroGPU. Subscribe to PRO for unlocking free
  cpu-basic flavor."*
- So a free Space must run **Gradio on ZeroGPU** — a GPU-inference runtime built
  around Gradio's own `@spaces.GPU` functions. This project is a CPU-only FastAPI
  service that needs none of that, and whether ZeroGPU will run a plain uvicorn
  server is unproven.

The Gradio entry point (`space_app.py`) and `./tools/prepare_space.sh gradio`
are still in the project, and both work — if you have PRO, or if you want to
test ZeroGPU yourself, they are ready. But **Render is the better free host for
this application**, and the repository ships a blueprint for it.

Verify the current terms yourself before committing a class either way; this is
exactly the kind of thing that changes.

## The short answer

**Hugging Face Spaces** — Docker SDK if your account has it, Gradio SDK
otherwise. Either way it is the closest thing to a genuinely free-forever host
for a Python app with a web UI: no card, no trial clock, and a public URL you can
hand out.

The catch worth knowing up front: a free Space **sleeps after a period of
inactivity** and takes a few seconds to wake. For a classroom that is a
non-issue — the first student to open it wakes it for everyone. A free Space is
also public, which is fine here because the app holds no secrets.

Pair it with **GitHub Codespaces** for the lab work, since the exercises need a
terminal anyway. That combination costs nothing and covers both halves of the
course.

If you want a URL for a single class **today**, with no hosting account at all,
open `tools/run_in_colab.ipynb` in Google Colab: it installs the project, runs a
sanity check, and opens a public tunnel that needs no signup. The URL lives as
long as the Colab session, which is right for a class day and wrong for a
permanent link.

---

## Option comparison

| Host | Free forever? | Good for | Watch out for |
|---|---|---|---|
| **HF Spaces** (Gradio SDK) | Yes, no card | The shared class URL when Docker is gated | Sleeps when idle; public; ephemeral disk |
| **HF Spaces** (Docker SDK) | Yes once enabled on your account | The same, with the cleanest build | Shows as "Paid" when signed out or not enabled |
| **Google Colab + tunnel** | Yes, no account beyond Google | A URL for one class, today | Dies with the runtime (~90 min idle); new URL each run |
| **GitHub Codespaces** | 60 core-hours/month per student | The labs — each student gets their own instance and a terminal | Hours are per account; stop the machine when done |
| **Google Cloud Run** | Generous always-free monthly allowance | A faster, no-sleep shared instance | Requires a billing account even to stay inside the free tier |
| **Oracle Cloud Always Free** | Yes, a real VM | A permanent instance that never sleeps | Signup friction; you administer the box |
| **Koyeb / Fly.io** | Small free allowance, terms shift | A second shared instance | Free tiers here have narrowed over time — check first |
| **Local / laptop** | Yes | Everything, including Ollama | Nothing to hand out |
| ~~Netlify / Vercel~~ | — | Static sites and serverless functions | This app is a long-lived Python process with subprocess MCP servers — it does not fit a serverless function cleanly |

Your instinct to move on from Netlify and Render was right for a different
reason than cost: this app keeps an in-memory retrieval index and spawns MCP
servers, so it wants a container, not a function.

---

## Deploying to Hugging Face Spaces

The `prepare_space.sh` helper assembles a push-ready folder for either SDK, so
you never hand-edit front matter or juggle two READMEs.

```bash
# free for everyone — use this if Docker shows as Paid
./tools/prepare_space.sh gradio ../qtcap-space

# or, if Docker is available on your account
./tools/prepare_space.sh docker ../qtcap-space
```

1. Create the Space at `huggingface.co/new-space`, **signed in**, picking the SDK
   you prepared for, hardware `CPU basic (free)`.
2. Push the prepared folder:

```bash
cd ../qtcap-space
git init && git add . && git commit -m "Capital Markets Agentic Capstone"
git remote add origin https://huggingface.co/spaces/<you>/<space-name>
git push origin main
```

3. Watch the build log. Gradio Spaces serve `space_app.py` on port 7860; Docker
   Spaces build the Dockerfile and expose the same port.
4. Open the URL, click **⚙ Model & key**, paste a Groq key, press **Verify key**.

### What the Gradio entry point actually does

`space_app.py` imports the project's FastAPI application, sets the hosted-mode
defaults, mounts a one-paragraph Gradio landing page at `/gradio` so the Space
looks like a Gradio Space to the platform, and runs uvicorn on 7860. The console
is at `/` and the API at `/api`, exactly as they are locally.

The Gradio landing page is deliberately optional: if Gradio is missing, its API
changes between versions, or it cannot reach the network, the file logs the
reason and serves the FastAPI application alone. A landing page is not worth a
failed boot. Gradio also makes outbound calls for analytics and a version check
when it is imported, which stall startup on a slow or restricted network, so
`space_app.py` disables both before importing it. Set `QTCAP_SKIP_GRADIO=1` to
bypass the landing page entirely.

Set these in **Settings → Variables** (not Secrets — none of them are secret):

```
QTCAP_PUBLIC_MODE=1          # rate limits, body caps, redaction
QTCAP_RATE_PER_MIN=40        # normal API calls per client per minute
QTCAP_HEAVY_RATE_PER_MIN=8   # model and test-run calls per client per minute
QTCAP_MARKET_MODE=auto       # live APIs, falling back to snapshot then synthetic
```

Leave every `*_API_KEY` variable **unset**. The server needs no key of its own:
students bring theirs.

---

## Render — the recommended free host

Render runs a real long-lived container, which is what this app needs, and the
repository ships `render.yaml` so there is nothing to configure by hand.

1. Push the project to a Git repository.
2. Render dashboard → **New → Blueprint** → pick the repo → **Apply**.

The blueprint sets the build and start commands, the health check at
`/api/health`, and the hosted-mode environment variables. It sets **no API
keys** — students bring their own from the browser, so the service holds no
credentials.

```yaml
buildCommand: pip install -r requirements.txt
startCommand: uvicorn app.api.main:app --host 0.0.0.0 --port $PORT --workers 1
healthCheckPath: /api/health
```

The free plan spins the service down after inactivity and takes roughly thirty
seconds to wake. For a classroom that is a non-issue: the first student to open
the link wakes it for everyone. `koyeb.yaml` carries the equivalent values for
Koyeb, whose UI is click-through rather than file-driven.

---

## Your own subdomain

`capstone.qualitythought.in` instead of
`capital-markets-agentic-capstone.onrender.com`. Render's Hobby (free) plan
includes two custom domains, so this costs nothing.

**1 — Tell Render the hostname.** Either uncomment the `domains:` block in
`render.yaml` and push, or add it in the dashboard under
**your service → Settings → Custom Domains → Add Custom Domain**.

**2 — Create one DNS record** at whoever hosts the zone for your domain
(GoDaddy, Cloudflare, Route 53, your web host's control panel):

| Type | Name | Value | TTL |
|---|---|---|---|
| `CNAME` | `capstone` | `capital-markets-agentic-capstone.onrender.com` | default |

The **Name** is the subdomain label only — `capstone`, not the full hostname;
most registrars append the domain for you. Use a `CNAME`, not an `A` record:
the platform's IP address changes and an `A` record silently rots. If you are
on Cloudflare, set the record to **DNS only** (grey cloud) until Render reports
the domain as verified, because proxying it first blocks the certificate check.

**3 — Wait for verification.** Render polls DNS and issues the TLS certificate
itself; usually a few minutes, up to an hour if your registrar is slow to
publish. The dashboard shows *Verified* and the padlock works with no further
action. Nothing about the app changes — no code, no rebuild.

**4 — Make it the only URL.** The platform hostname keeps working forever, so
the same class now has two live URLs. That is a reproducibility problem, not a
convenience: a student files a finding against one and the screenshot in it
came from the other. Set, in the service's environment:

```
QTCAP_CANONICAL_HOST = capstone.qualitythought.in
```

Every `GET` arriving on any other hostname then answers `308` to the canonical
one. `POST` is deliberately *not* redirected — a redirected `POST` drops the
per-request model key the console sends as a header, and the student sees a
confusing failure instead of a redirect. The health check is never redirected
either, because the platform probes by its own hostname.

Set this only **after** the domain verifies. Point it at a hostname that does
not resolve yet and you have redirected your working URL to a dead one.

**5 — Optionally, refuse hostnames nobody configured.** Anyone can point a DNS
record of their own at a hosting platform; without a host check your app
answers under their name, which is a neat way to phish your own trainees.

```
QTCAP_ALLOWED_HOSTS = capstone.qualitythought.in,capital-markets-agentic-capstone.onrender.com
```

Comma-separated. A leading dot means "this domain and its subdomains"
(`.qualitythought.in`). Loopback names stay allowed so the health check and the
Playwright suite still run. Unset — the default — means answer to anything,
which is what a laptop wants.

Nine tests in `tests/test_hosting_security.py` cover this: the off-by-default
behaviour, case and port normalisation, the subdomain wildcard, the redirect,
and the two things that must *not* be redirected.

> A subdomain of a domain you already own is the cheapest option and the one to
> take. A brand-new domain is the same setup plus an `ALIAS`/`ANAME` record at
> the apex, which not every registrar supports — if yours does not, point
> `www` at the platform with a `CNAME` and redirect the apex to it.

---

## Deploying anywhere else with the same image

```bash
docker build -t qtcap .
docker run -p 7860:7860 -e QTCAP_PUBLIC_MODE=1 qtcap
```

- **Cloud Run** — `gcloud run deploy --source . --port 7860 --allow-unauthenticated`
- **Koyeb / Fly.io** — point at the Dockerfile, expose 7860
- **Oracle / any VM** — `docker run -d --restart=unless-stopped -p 80:7860 qtcap`

---

## Colab, for a URL today

`tools/run_in_colab.ipynb` gets you a public URL in about two minutes with no
hosting account. Upload the project zip (or point it at a git repo), run the
cells, and share the `trycloudflare.com` link the notebook prints.

It is deliberately not just "start a server":

- it runs a slice of the shipped suite before printing a URL, so you do not hand
  out a broken link
- it sets `QTCAP_PUBLIC_MODE=1`, so rate limits and body caps are on
- it has a cell that lists findings as students file them, so you can watch the
  class work in real time
- it has a cell that exports those findings before the runtime is wiped

Trade-offs to say out loud: the URL changes every run, the runtime stops after
about ninety minutes idle, and the tunnel is public while it is up. Stop the
runtime when the session ends.

## Codespaces for the labs

`.devcontainer/devcontainer.json` is included, so a student clicks **Code →
Codespaces → Create** and gets Python 3.11, the dependencies, Chromium for the
UI tests, and port 8000 forwarded. They then have the terminal the labs need:

```bash
./test.sh fast
python tools/seed_defect.py D1
pytest tests/test_ui.py -v
```

---

## Bringing your own key

The hosted instance stores no keys. A student's key lives in their browser's
`localStorage`, travels as an `X-LLM-Key` header on each request, is used once
to call the provider, and is dropped. It is never logged, never written to disk,
and never returned in a response — every outbound error string passes through a
redactor that replaces anything credential-shaped.

| Provider | Free? | Get a key | Notes |
|---|---|---|---|
| **Groq** | Free developer tier | console.groq.com/keys | Recommended. Fast, good tool-calling on Llama 3.3 70B |
| **Cerebras** | Free tier | cloud.cerebras.ai | Fastest when available, smaller catalogue |
| **Google AI Studio** | Free Flash tier | aistudio.google.com/apikey | Reached through Google's OpenAI-compatible endpoint |
| **OpenRouter** | `:free` models | openrouter.ai/keys | Many models, one key — ideal for the comparison lab |
| **Mistral / Together** | Limited free | their consoles | Together's free models carry a `-Free` suffix |
| **xAI (Grok)** | Credits only | console.x.ai | Treat as paid unless you have confirmed credits |
| **Ollama** | Free forever | ollama.com | **Local only** — see below |
| **Stub** | Free forever | — | Offline, deterministic, no signup. The suite's default |

### Ollama and the hosted instance

A hosted instance **cannot** reach a student's `localhost:11434`. Their laptop is
not addressable from a server in a datacentre, and it should not be. The app
says so rather than failing obscurely: picking Ollama in the settings of a hosted
instance returns a message explaining that they need to run the project locally.

So: **Ollama is for local runs, a free hosted key is for the shared URL.** For a
class, tell students to get a Groq key in the first ten minutes — it is one page
and no card — and keep Ollama for anyone who wants to work offline afterwards.

### Why the key goes through the server

The browser could call Groq directly, which would keep the key off the server
entirely. It would also mean shipping the retrieval index, the eleven tools, the
MCP servers and the guardrails into the browser, which is the whole application.
So the server proxies, and pays for that with three rules it actually enforces:
one-request key lifetime, an allowlist of provider hosts so a crafted request
cannot make the server fetch an internal address, and redaction on every
outbound string.

Tell students to use a key they can revoke, and to revoke it at the end of the
course. That is good practice regardless of how much you trust the instance, and
saying so out loud is part of the teaching.

---

## What a shared instance changes about the app

Three behaviours differ from a local run, and each one is worth a minute of
class time because they are the things that make a multi-user AI service
different from a single-user one.

**Guardrail mode is per request.** Each panel has its own `guardrails` switch and
it travels in the request body. A global switch — which is what the first
version of this app had — would let one student disable another student's
controls mid-lab. That is a genuine multi-tenant defect, and the fix is worth
showing.

**Rate limits are per client.** A student who loops the agent gets a 429 with a
message telling them to run locally, rather than exhausting the instance.

**Findings are ephemeral.** `data/issues.jsonl` lives on the container's disk,
which a free tier wipes on restart. The Findings tab pushes students to export to
Markdown, CSV or JSON. For a persistent log, point `QTCAP_NOTIFY_WEBHOOK` at a
Slack or Teams incoming webhook and every high or critical finding is posted as
it is filed:

```
QTCAP_NOTIFY_WEBHOOK=https://hooks.slack.com/services/...
QTCAP_NOTIFY_MIN_SEVERITY=high
```

That variable is operator-only by design. If students could set the destination,
the endpoint would become an outbound request forwarder pointed wherever they
liked.

---

## Before a class

```bash
python tools/fetch_live_data.py    # refresh snapshots, ideally during market hours
./test.sh fast                     # 327 green
./test.sh ui                       # 31 green
git push space main                # deploy
```

Then open the URL yourself, set a Groq key, run one query on each of the three
panels, and file one finding. Five minutes, and it catches the deployment
problems before thirty students find them for you.
