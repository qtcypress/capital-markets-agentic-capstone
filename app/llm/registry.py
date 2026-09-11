"""Catalogue of LLM providers, including the free ones students can bring keys for.

Design rule for the hosted deployment: a student's API key is supplied per
request from their browser, used once, and never written to disk, never logged,
and never held in a module-level variable. The server is a proxy, not a vault.

Every entry is OpenAI-chat-completions compatible unless `style` says otherwise,
which is why supporting Groq, xAI, Cerebras, OpenRouter, Together and Mistral
costs one table row each rather than one client each.

NOTE ON FREE TIERS: rate limits, free model lists and signup terms change often.
The `free_tier` text below is guidance for trainees, not a contract — verify at
the provider's own pricing page before a class. Nothing in the application logic
depends on these strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Style = Literal["openai", "anthropic", "gemini", "ollama", "stub"]


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    style: Style
    base_url: str = ""
    default_model: str = ""
    models: tuple[str, ...] = ()
    key_env: str = ""
    key_prefix: str = ""
    console_url: str = ""
    free_tier: str = ""
    byok: bool = True          # can a student supply their own key from the browser?
    local_only: bool = False   # requires something running on the student's machine
    notes: str = ""


PROVIDERS: dict[str, Provider] = {
    # ---------------------------------------------------------------- free, keyed
    "groq": Provider(
        key="groq",
        label="Groq",
        style="openai",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        models=(
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3-32b",
        ),
        key_env="GROQ_API_KEY",
        key_prefix="gsk_",
        console_url="https://console.groq.com/keys",
        free_tier="Free developer tier with per-minute and per-day request limits. "
                  "Fast enough that a 327-case suite finishes in minutes.",
        notes="Recommended default for a classroom: free, quick signup, very fast inference, "
              "and solid tool-calling on the 70B model.",
    ),
    "cerebras": Provider(
        key="cerebras",
        label="Cerebras",
        style="openai",
        base_url="https://api.cerebras.ai/v1",
        default_model="llama-3.3-70b",
        models=("llama-3.3-70b", "llama3.1-8b", "qwen-3-32b"),
        key_env="CEREBRAS_API_KEY",
        key_prefix="csk-",
        console_url="https://cloud.cerebras.ai",
        free_tier="Free tier with daily token allowance.",
        notes="The fastest option when it is available; smaller model catalogue than Groq.",
    ),
    "gemini": Provider(
        key="gemini",
        label="Google AI Studio (Gemini)",
        style="openai",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.0-flash",
        models=("gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash"),
        key_env="GEMINI_API_KEY",
        key_prefix="AIza",
        console_url="https://aistudio.google.com/apikey",
        free_tier="Free tier on the Flash models with daily request limits.",
        notes="Uses Google's OpenAI-compatible endpoint, so it needs no separate client.",
    ),
    "openrouter": Provider(
        key="openrouter",
        label="OpenRouter",
        style="openai",
        base_url="https://openrouter.ai/api/v1",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        models=(
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-72b-instruct:free",
        ),
        key_env="OPENROUTER_API_KEY",
        key_prefix="sk-or-",
        console_url="https://openrouter.ai/keys",
        free_tier="Models suffixed ':free' cost nothing, subject to shared rate limits.",
        notes="Useful for the model-comparison lab: many models behind one key and one base URL. "
              "Free models are rate limited and tool-calling support varies by model.",
    ),
    "xai": Provider(
        key="xai",
        label="xAI (Grok)",
        style="openai",
        base_url="https://api.x.ai/v1",
        default_model="grok-3-mini",
        models=("grok-3-mini", "grok-3", "grok-4"),
        key_env="XAI_API_KEY",
        key_prefix="xai-",
        console_url="https://console.x.ai",
        free_tier="Paid in practice — promotional credits only, not a standing free tier. Check before a class.",
        notes="OpenAI-compatible. Treat as paid unless you have confirmed current credits.",
    ),
    "mistral": Provider(
        key="mistral",
        label="Mistral",
        style="openai",
        base_url="https://api.mistral.ai/v1",
        default_model="mistral-small-latest",
        models=("mistral-small-latest", "open-mistral-nemo", "mistral-large-latest"),
        key_env="MISTRAL_API_KEY",
        console_url="https://console.mistral.ai/api-keys",
        free_tier="Free experimentation tier on some models.",
    ),
    "together": Provider(
        key="together",
        label="Together AI",
        style="openai",
        base_url="https://api.together.xyz/v1",
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        models=("meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",),
        key_env="TOGETHER_API_KEY",
        console_url="https://api.together.ai/settings/api-keys",
        free_tier="A small number of models carry a '-Free' suffix.",
    ),
    # ---------------------------------------------------------------- paid
    "openai": Provider(
        key="openai",
        label="OpenAI",
        style="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        models=("gpt-4o-mini", "gpt-4o"),
        key_env="OPENAI_API_KEY",
        key_prefix="sk-",
        console_url="https://platform.openai.com/api-keys",
        free_tier="Paid.",
    ),
    "anthropic": Provider(
        key="anthropic",
        label="Anthropic",
        style="anthropic",
        base_url="https://api.anthropic.com/v1",
        default_model="claude-sonnet-4-5",
        models=("claude-sonnet-4-5", "claude-haiku-4-5"),
        key_env="ANTHROPIC_API_KEY",
        key_prefix="sk-ant-",
        console_url="https://console.anthropic.com/settings/keys",
        free_tier="Paid.",
    ),
    # ---------------------------------------------------------------- local
    "ollama": Provider(
        key="ollama",
        label="Ollama (local)",
        style="ollama",
        base_url="http://localhost:11434",
        default_model="llama3.1:8b",
        models=("llama3.1:8b", "qwen2.5:7b", "mistral:7b", "phi4"),
        key_env="",
        console_url="https://ollama.com/download",
        free_tier="Free forever — it runs on the student's own machine.",
        byok=False,
        local_only=True,
        notes="Only works when the application itself runs on the same machine as Ollama. "
              "A student using the hosted instance cannot reach their own localhost — they "
              "must run the project locally to use Ollama.",
    ),
    # ---------------------------------------------------------------- offline
    "stub": Provider(
        key="stub",
        label="Deterministic stub (no key)",
        style="stub",
        default_model="deterministic-stub-v1",
        models=("deterministic-stub-v1",),
        free_tier="Free forever, offline, no signup.",
        byok=False,
        notes="Rule-based and fully reproducible. This is what the 327-case regression suite "
              "runs against by default, and what a student uses before they have any key.",
    ),
}

FREE_PROVIDERS = tuple(k for k, p in PROVIDERS.items() if "Paid" not in p.free_tier)

# Only these hosts may ever be dialled with a user-supplied key. A student could
# otherwise pass a base_url pointing at an internal address and turn the server
# into an SSRF proxy.
ALLOWED_HOSTS = frozenset(
    {
        "api.groq.com", "api.cerebras.ai", "generativelanguage.googleapis.com",
        "openrouter.ai", "api.x.ai", "api.mistral.ai", "api.together.xyz",
        "api.openai.com", "api.anthropic.com",
    }
)


def get_provider(key: str) -> Provider | None:
    return PROVIDERS.get((key or "").strip().lower())


def public_catalogue() -> list[dict]:
    """Provider list for the browser. Contains no secrets — only public metadata."""
    return [
        {
            "key": p.key,
            "label": p.label,
            "default_model": p.default_model,
            "models": list(p.models),
            "needs_key": bool(p.key_env) and p.byok,
            "key_prefix": p.key_prefix,
            "console_url": p.console_url,
            "free_tier": p.free_tier,
            "local_only": p.local_only,
            "notes": p.notes,
            "is_free": "Paid" not in p.free_tier,
        }
        for p in PROVIDERS.values()
    ]


def validate_key_shape(provider_key: str, api_key: str) -> str | None:
    """Cheap client-error detection so a student sees 'wrong key' rather than a 401.

    Returns an error message, or None when the key looks plausible. This is a
    shape check, never a validity check — only the provider can say that.
    """
    p = get_provider(provider_key)
    if p is None:
        return f"Unknown provider '{provider_key}'."
    if not p.byok or not p.key_env:
        return None
    if not api_key:
        return f"{p.label} needs an API key. Get one free at {p.console_url}."
    if len(api_key) < 16:
        return "That key looks too short to be valid."
    if p.key_prefix and not api_key.startswith(p.key_prefix):
        return (
            f"A {p.label} key normally starts with '{p.key_prefix}'. "
            "Check you pasted the right provider's key."
        )
    return None
