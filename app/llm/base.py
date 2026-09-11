"""Pluggable LLM abstraction.

One narrow interface, four backends. Tests target the interface, so the same
200 blue-team and 100 red-team cases run against a cloud model, a local Ollama
model, or the deterministic stub.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = ""


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class LLMError(RuntimeError):
    pass


class BaseLLM:
    """Contract every provider implements."""

    provider = "base"

    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024, timeout_s: float = 60.0):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def complete(self, messages: list[Message], tools: list[dict] | None = None) -> LLMResponse:
        started = time.perf_counter()
        try:
            resp = self._complete(messages, tools)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller as a structured error
            resp = LLMResponse(error=f"{type(exc).__name__}: {exc}")
        resp.provider = self.provider
        resp.model = self.model
        resp.latency_ms = int((time.perf_counter() - started) * 1000)
        return resp

    def _complete(self, messages: list[Message], tools: list[dict] | None) -> LLMResponse:
        raise NotImplementedError

    # -- helpers shared by providers ------------------------------------
    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any] | None:
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
