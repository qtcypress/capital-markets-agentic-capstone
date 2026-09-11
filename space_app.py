"""Entry point for a Hugging Face Space running on the **Gradio** SDK.

Why this file exists
--------------------
The Docker SDK is the natural fit for this project, but it is gated on Hugging
Face: signed-out visitors, and accounts without it enabled, see Docker marked
"Paid" on the new-Space page. The Gradio SDK is free to everyone.

A Gradio Space simply runs one Python file and proxies whatever is listening on
port 7860. Gradio itself is built on FastAPI, so there is nothing stopping that
file from serving *our* FastAPI application instead — which is what this does.
The console, the API, the MCP servers and the test runner all behave exactly as
they do locally.

A tiny Gradio page is mounted at /gradio as well, so the Space still looks like
a Gradio Space to the platform and gives visitors a landing page if they arrive
there. It is not where the application lives.

Referenced from the Space's README front matter:

    sdk: gradio
    app_file: space_app.py

Run it locally exactly as the Space will:

    python space_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# A hosted Space serves a whole class from one URL, so switch on the protections
# a shared instance needs: per-client rate limits, a request-body cap and strict
# redaction of anything credential-shaped on the way out. Students bring their
# own model keys from the browser, so the Space itself holds none.
os.environ.setdefault("QTCAP_PUBLIC_MODE", "1")
os.environ.setdefault("QTCAP_LLM_PROVIDER", "stub")
os.environ.setdefault("QTCAP_MARKET_MODE", "auto")
# A Space's filesystem is ephemeral and its home directory is the writable one.
os.environ.setdefault("QTCAP_MCP_TRANSPORT", "in_process")

from app.api.main import app  # noqa: E402  (import after the env defaults above)

PORT = int(os.environ.get("PORT", "7860"))

LANDING = """
<div style="font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
            max-width:640px;margin:48px auto;padding:0 20px;line-height:1.6">
  <h2 style="margin:0 0 8px">Capital Markets Agentic Capstone</h2>
  <p style="color:#5d6b7c;margin:0 0 20px">
    RAG, a tool-calling agent and an MCP multi-agent system, built for testing practice.
  </p>
  <p><a href="/" style="display:inline-block;background:#0b5ed7;color:#fff;
     padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600">
     Open the console &rarr;</a></p>
  <p style="color:#5d6b7c;font-size:14px;margin-top:24px">
    No API key is needed to start — the default backend is a deterministic offline stub.
    For a real model, open <strong>Model &amp; key</strong> in the console and paste a free
    key (Groq is the quickest). Your key stays in your browser and is never stored here.
  </p>
</div>
"""


def _mount_gradio_landing(fastapi_app):
    """Mount a minimal Gradio page at /gradio.

    Optional by design: if Gradio is missing, its API shifts between versions, or
    it cannot reach the network, the capstone must still serve. A landing page is
    not worth a failed boot — and on import Gradio makes outbound calls for
    analytics and a version check, which stall startup on a restricted or slow
    network. Those are switched off below before it is imported.

    Set QTCAP_SKIP_GRADIO=1 to bypass this entirely.
    """
    if os.environ.get("QTCAP_SKIP_GRADIO", "").strip().lower() in {"1", "true", "yes"}:
        print("[space] QTCAP_SKIP_GRADIO set; serving FastAPI only.")
        return fastapi_app

    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("DO_NOT_TRACK", "1")

    try:
        import gradio as gr
    except Exception as exc:  # noqa: BLE001
        print(f"[space] Gradio not available ({type(exc).__name__}); serving FastAPI only.")
        return fastapi_app

    try:
        with gr.Blocks(title="Capital Markets Agentic Capstone") as demo:
            gr.HTML(LANDING)
        return gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
    except Exception as exc:  # noqa: BLE001
        print(f"[space] Could not mount the Gradio landing page ({type(exc).__name__}: {exc}).")
        print("[space] Continuing with the FastAPI application alone.")
        return fastapi_app


application = _mount_gradio_landing(app)


def main() -> None:
    import uvicorn

    print(f"[space] Capital Markets Agentic Capstone on 0.0.0.0:{PORT}")
    print("[space] Console at /  ·  API at /api  ·  Gradio landing at /gradio")
    # One worker: the retrieval index and the MCP servers are per-process, and a
    # free tier has neither the memory nor the CPU for more.
    uvicorn.run(application, host="0.0.0.0", port=PORT, workers=1, log_level="info")


if __name__ == "__main__":
    main()
