"""Central configuration for the Capital Markets Agentic Capstone.

Everything is driven by environment variables so a trainee can switch the whole
application between a real cloud LLM, a local Ollama model, or the deterministic
offline stub without touching code.

    QTCAP_LLM_PROVIDER = openai | anthropic | ollama | stub
    QTCAP_LLM_MODEL    = model name for that provider
    OPENAI_API_KEY / ANTHROPIC_API_KEY = credentials when using a cloud provider
    QTCAP_OLLAMA_HOST  = http://localhost:11434
    QTCAP_MARKET_MODE  = live | snapshot | auto      (default: auto)
    QTCAP_ALLOW_STALE  = 1 to serve cached data when the live API fails
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE = ROOT / "knowledge_base"
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
REPORT_DIR = ROOT / "reports"

for _d in (DATA_DIR, SNAPSHOT_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _flag(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass
class LLMConfig:
    provider: str = field(default_factory=lambda: _env("QTCAP_LLM_PROVIDER", "stub").lower())
    model: str = field(default_factory=lambda: _env("QTCAP_LLM_MODEL"))
    temperature: float = field(default_factory=lambda: float(_env("QTCAP_LLM_TEMPERATURE", "0") or 0))
    max_tokens: int = field(default_factory=lambda: int(_env("QTCAP_LLM_MAX_TOKENS", "1024") or 1024))
    timeout_s: float = field(default_factory=lambda: float(_env("QTCAP_LLM_TIMEOUT", "60") or 60))
    ollama_host: str = field(default_factory=lambda: _env("QTCAP_OLLAMA_HOST", "http://localhost:11434"))
    openai_base_url: str = field(default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    anthropic_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))

    def default_model(self) -> str:
        if self.model:
            return self.model
        return {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-sonnet-4-5",
            "ollama": "llama3.1:8b",
            "stub": "deterministic-stub-v1",
        }.get(self.provider, "deterministic-stub-v1")


@dataclass
class MarketConfig:
    mode: str = field(default_factory=lambda: _env("QTCAP_MARKET_MODE", "auto").lower())
    allow_stale: bool = field(default_factory=lambda: _flag("QTCAP_ALLOW_STALE", True))
    timeout_s: float = field(default_factory=lambda: float(_env("QTCAP_MARKET_TIMEOUT", "12") or 12))
    snapshot_ttl_s: int = field(default_factory=lambda: int(_env("QTCAP_SNAPSHOT_TTL", "900") or 900))
    risk_free_rate: float = field(default_factory=lambda: float(_env("QTCAP_RISK_FREE_RATE", "0.065") or 0.065))
    user_agent: str = field(
        default_factory=lambda: _env(
            "QTCAP_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        )
    )


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    rag_top_k: int = field(default_factory=lambda: int(_env("QTCAP_RAG_TOP_K", "4") or 4))
    rag_min_score: float = field(default_factory=lambda: float(_env("QTCAP_RAG_MIN_SCORE", "0.06") or 0.06))
    agent_max_steps: int = field(default_factory=lambda: int(_env("QTCAP_AGENT_MAX_STEPS", "6") or 6))
    guardrails_enabled: bool = field(default_factory=lambda: _flag("QTCAP_GUARDRAILS", True))

    # Deliberately weakened configuration used by red-team labs, so trainees can
    # see the same attack pass and fail.
    vulnerable_mode: bool = field(default_factory=lambda: _flag("QTCAP_VULNERABLE_MODE", False))


_config: AppConfig | None = None


def get_config(refresh: bool = False) -> AppConfig:
    global _config
    if _config is None or refresh:
        _config = AppConfig()
    return _config
