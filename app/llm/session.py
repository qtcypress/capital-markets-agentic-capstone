"""Per-request LLM resolution for the bring-your-own-key deployment.

On a shared hosted instance the model backend is chosen by the *student*, not by
the server's environment. This module turns a request's declared provider, model
and key into a client, enforcing three rules:

  1. The key is used for one request and then dropped. It is never persisted,
     never logged, and never stored in a module-level cache keyed by anything a
     later request could reach.
  2. Only hosts in the registry allowlist may be dialled, so a crafted request
     cannot turn the server into an SSRF proxy toward an internal address.
  3. Anything that gets rendered back to the user passes through `redact`, so a
     key that ends up in a provider's error string never reaches a log line, a
     trace, or another student's screen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from ..config import get_config
from .base import BaseLLM
from .providers import AnthropicLLM, OllamaLLM, OpenAILLM, StubLLM
from .registry import ALLOWED_HOSTS, get_provider, validate_key_shape

# Anything that looks like a credential, whatever provider it came from.
_SECRET_RE = re.compile(
    r"\b("
    r"gsk_[A-Za-z0-9_\-]{10,}"
    r"|sk-ant-[A-Za-z0-9_\-]{10,}"
    r"|sk-or-[A-Za-z0-9_\-]{10,}"
    r"|sk-[A-Za-z0-9_\-]{16,}"
    r"|csk-[A-Za-z0-9_\-]{10,}"
    r"|xai-[A-Za-z0-9_\-]{10,}"
    r"|AIza[A-Za-z0-9_\-]{20,}"
    r"|Bearer\s+[A-Za-z0-9_\-\.]{16,}"
    r")\b"
)


def redact(text: Any) -> str:
    """Replace anything credential-shaped with a marker. Use on every outbound string."""
    return _SECRET_RE.sub("[REDACTED_KEY]", str(text or ""))


class LLMSessionError(ValueError):
    """A problem with the caller's provider/model/key choice, safe to show them."""


@dataclass
class LLMChoice:
    """What one request asked for. `api_key` lives only as long as the request."""

    provider: str
    model: str = ""
    api_key: str = ""
    base_url: str = ""

    def describe(self) -> dict[str, Any]:
        """Public description — deliberately excludes the key."""
        return {"provider": self.provider, "model": self.model,
                "key_supplied": bool(self.api_key)}


def _check_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise LLMSessionError(
            f"Refusing to call '{host or url}'. Only known model providers may be reached."
        )


def resolve_choice(
    provider: str | None,
    model: str | None = None,
    api_key: str | None = None,
) -> LLMChoice:
    """Work out what to run, falling back to the server's own configuration."""
    cfg = get_config()
    provider = (provider or cfg.llm.provider or "stub").strip().lower()
    spec = get_provider(provider)
    if spec is None:
        raise LLMSessionError(
            f"Unknown provider '{provider}'. Choose one of: {', '.join(sorted(get_provider.__globals__['PROVIDERS']))}"
        )

    api_key = (api_key or "").strip()
    # Fall back to a server-side key only when the operator deliberately set one
    # (single-user local runs); a hosted instance normally has none.
    if not api_key and spec.key_env:
        import os

        api_key = os.environ.get(spec.key_env, "").strip()

    problem = validate_key_shape(provider, api_key)
    if problem:
        raise LLMSessionError(problem)

    model = (model or "").strip() or spec.default_model
    if spec.models and model not in spec.models:
        # Not an error: providers add models faster than this table is updated.
        pass

    return LLMChoice(provider=provider, model=model, api_key=api_key, base_url=spec.base_url)


def build_llm_for(choice: LLMChoice) -> BaseLLM:
    """Construct a client for one request. Never cached."""
    cfg = get_config().llm
    spec = get_provider(choice.provider)
    if spec is None:
        raise LLMSessionError(f"Unknown provider '{choice.provider}'.")

    common = dict(
        model=choice.model or spec.default_model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        timeout_s=cfg.timeout_s,
    )

    if spec.style == "stub":
        return StubLLM(**common)

    if spec.style == "ollama":
        host = choice.base_url or spec.base_url
        # Ollama is reached over loopback on the student's own machine, so it is
        # exempt from the allowlist but restricted to loopback.
        hostname = (urlparse(host).hostname or "").lower()
        if hostname not in ("localhost", "127.0.0.1", "::1", "host.docker.internal"):
            raise LLMSessionError(
                "Ollama must run on the same machine as this application. "
                "A hosted instance cannot reach your laptop's localhost — run the project "
                "locally to use Ollama, or pick a free hosted provider such as Groq."
            )
        return OllamaLLM(host=host, **common)

    base_url = choice.base_url or spec.base_url
    _check_host(base_url)

    if spec.style == "anthropic":
        return AnthropicLLM(api_key=choice.api_key, **common)

    # Everything else speaks the OpenAI chat-completions dialect.
    return OpenAILLM(api_key=choice.api_key, base_url=base_url, **common)


def build_from_request(
    provider: str | None,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[BaseLLM, LLMChoice]:
    choice = resolve_choice(provider, model, api_key)
    return build_llm_for(choice), choice
