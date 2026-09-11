"""Concrete LLM backends: OpenAI, Anthropic, Ollama, and a deterministic stub."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .base import BaseLLM, LLMResponse, Message, ToolCall


# ----------------------------------------------------------------------------
# OpenAI-compatible (also works against Azure OpenAI, Groq, vLLM, LM Studio ...)
# ----------------------------------------------------------------------------
class OpenAILLM(BaseLLM):
    provider = "openai"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", **kw):
        super().__init__(**kw)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _complete(self, messages: list[Message], tools: list[dict] | None) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
            payload["tool_choice"] = "auto"
        r = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        choice = data["choices"][0]["message"]
        calls = [
            ToolCall(
                name=tc["function"]["name"],
                arguments=json.loads(tc["function"].get("arguments") or "{}"),
                id=tc.get("id", ""),
            )
            for tc in (choice.get("tool_calls") or [])
        ]
        return LLMResponse(text=choice.get("content") or "", tool_calls=calls, raw=data)


# ----------------------------------------------------------------------------
# Anthropic Messages API
# ----------------------------------------------------------------------------
class AnthropicLLM(BaseLLM):
    provider = "anthropic"

    def __init__(self, api_key: str, **kw):
        super().__init__(**kw)
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        self.api_key = api_key

    def _complete(self, messages: list[Message], tools: list[dict] | None) -> LLMResponse:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        convo = []
        for m in messages:
            if m.role == "system":
                continue
            role = "assistant" if m.role == "assistant" else "user"
            content = m.content if m.role != "tool" else f"[tool result: {m.name}]\n{m.content}"
            convo.append({"role": role, "content": content})
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": convo or [{"role": "user", "content": "(empty)"}],
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": t["name"], "description": t.get("description", ""), "input_schema": t["parameters"]}
                for t in tools
            ]
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        data = r.json()
        text_parts, calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                calls.append(ToolCall(name=block["name"], arguments=block.get("input", {}), id=block.get("id", "")))
        return LLMResponse(text="\n".join(text_parts), tool_calls=calls, raw=data)


# ----------------------------------------------------------------------------
# Ollama (local models, no API key, no cost)
# ----------------------------------------------------------------------------
class OllamaLLM(BaseLLM):
    provider = "ollama"

    def __init__(self, host: str = "http://localhost:11434", **kw):
        super().__init__(**kw)
        self.host = host.rstrip("/")

    def _complete(self, messages: list[Message], tools: list[dict] | None) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        r = httpx.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        calls = [
            ToolCall(name=tc["function"]["name"], arguments=tc["function"].get("arguments") or {})
            for tc in (msg.get("tool_calls") or [])
        ]
        text = msg.get("content") or ""
        # Small local models often emit a JSON tool call inside the text body.
        if not calls and tools:
            parsed = self._parse_json_object(text)
            if parsed and "tool" in parsed:
                calls = [ToolCall(name=str(parsed["tool"]), arguments=parsed.get("arguments") or {})]
                text = ""
        return LLMResponse(text=text, tool_calls=calls, raw=data)


# ----------------------------------------------------------------------------
# Deterministic stub — no network, no key, identical output every run.
# This is what makes the 300-case regression suite reproducible in CI.
# ----------------------------------------------------------------------------
# Ordered most-specific first: the first rule that matches wins, so a query
# mentioning both "margin" and "futures" routes to the margin tool.
_INTENT_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    # (tool name, regex, argument keys to lift from the query)
    ("calc_margin", r"\b(margin|span|exposure|collateral|how much (money|capital|funds))\b", ("symbol", "lots", "position")),
    ("payoff_profile", r"\b(payoff|pay[- ]off|breakeven|break[- ]even|max(imum)? (profit|loss)|"
                       r"straddle|strangle|iron condor|butterfly|(bull|bear) (call|put) spread)\b", ("symbol",)),
    ("implied_volatility", r"\bimplied vol(atility)?\b.{0,40}\b(from|given|back out|premium of|trading at)\b", ("symbol", "strike")),
    ("calc_greeks", r"\b(greeks?|delta|gamma|vega|theta|rho)\b", ("symbol", "strike", "lots")),
    ("price_option", r"\b(black[- ]scholes|fair value|theoretical (price|value)|"
                     r"premium (should|would)|price (the|this|a|an)\s+[\w\s]{0,30}?(call|put|option)|"
                     r"value (the|this) option)\b", ("symbol", "strike")),
    ("get_option_chain", r"\b(option chain|strikes?|open interest|\boi\b|pcr|put[- ]call ratio|max pain)\b", ("symbol", "expiry")),
    ("get_futures", r"\b(futures?|basis|rollover|cost of carry|contango|backwardation)\b", ("symbol",)),
    ("get_fx_rate", r"\b(usd\s*/?\s*inr|exchange rate|\bfx\b|currency rate|rupee (rate|value)|dollar rate)\b", ()),
    ("get_contract_spec", r"\b(lot size|tick size|contract (spec|size)|strike step|expiry day)\b", ("symbol",)),
    ("get_quote", r"\b(price|quote|ltp|trading at|last traded|spot|current level|how much is)\b", ("symbol",)),
    ("search_knowledge_base", r"\b(what|explain|define|how|why|rule|regulation|sebi|circular|policy|"
                              r"eligib|settle|mean|difference)\b", ("query",)),
]

# A conceptual question ("explain gamma") must go to the knowledge base, not to
# a calculator, even though it names a Greek.
_CONCEPTUAL_OPENER = re.compile(
    r"^\s*(what\s+(is|are|does|do)|explain|define|describe|tell me about|how\s+(does|do|is|are)|why|when\s+(does|do)|"
    r"can you explain|what'?s the difference)\b",
    re.IGNORECASE,
)
# Tools a purely conceptual question should never reach. get_fx_rate is
# excluded: "what is the USD/INR rate" reads conceptual but wants live data.
_CALCULATOR_TOOLS = {
    "calc_greeks", "price_option", "payoff_profile", "implied_volatility",
    "calc_margin", "get_option_chain", "get_futures", "get_quote", "get_contract_spec",
}

_LIVE_DATA_HINT = re.compile(
    r"\b(current|currently|now|today|live|latest|right now|price|quote|ltp|spot|"
    r"margin for|my position|calculate|compute|payoff|breakeven)\b",
    re.IGNORECASE,
)

_SYMBOL_RE = re.compile(
    r"\b(NIFTY\s*50|BANK\s*NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY|NIFTY|SENSEX|"
    r"RELIANCE|TCS|INFY|HDFCBANK|ICICIBANK|SBIN|ITC|AXISBANK|KOTAKBANK|LT|"
    r"BHARTIARTL|MARUTI|TATAMOTORS|WIPRO|HINDUNILVR)\b",
    re.IGNORECASE,
)
_STRIKE_RE = re.compile(r"\b(\d{3,6})\s*(?:strike|ce|pe|call|put)\b", re.IGNORECASE)
_LOTS_RE = re.compile(r"\b(\d{1,4})\s*lots?\b", re.IGNORECASE)
_SIDE_RE = re.compile(r"\b(short|sell|sold|selling|written|write|wrote|writing)\b", re.IGNORECASE)
_EXPIRY_RE = re.compile(r"\b(\d{1,2}[-/ ][A-Za-z]{3}[-/ ]\d{2,4}|\d{4}-\d{2}-\d{2}|weekly|monthly|current|next)\b", re.IGNORECASE)


class StubLLM(BaseLLM):
    """Rule-based, fully deterministic stand-in for a real model.

    It is intentionally *naive about instructions found in context*: with
    guardrails disabled it will obey an injected instruction, which is exactly
    what the red-team labs need in order to demonstrate a real failure and then
    a real fix.
    """

    provider = "stub"

    def _complete(self, messages: list[Message], tools: list[dict] | None) -> LLMResponse:
        user_msgs = [m for m in messages if m.role == "user"]
        query = user_msgs[-1].content if user_msgs else ""
        tool_results = [m for m in messages if m.role == "tool"]
        system = "\n".join(m.content for m in messages if m.role == "system")

        if tools and not tool_results:
            call = self._route(query, {t["name"] for t in tools})
            if call:
                return LLMResponse(tool_calls=[call])

        if tool_results:
            return LLMResponse(text=self._summarise_tools(query, tool_results))

        return LLMResponse(text=self._answer_from_context(query, system, messages))

    # -- routing --------------------------------------------------------
    def _route(self, query: str, available: set[str]) -> ToolCall | None:
        q = query.lower()
        conceptual = (
            _CONCEPTUAL_OPENER.search(query)
            and not _LIVE_DATA_HINT.search(query)
            and not _STRIKE_RE.search(query)
            and not _SYMBOL_RE.search(query)
        )
        for tool, pattern, keys in _INTENT_RULES:
            if tool not in available:
                continue
            if not re.search(pattern, q, re.IGNORECASE):
                continue
            # "Explain gamma" names a Greek but wants a concept, not a
            # calculation. Only the calculator tools are diverted this way.
            if conceptual and tool in _CALCULATOR_TOOLS and "search_knowledge_base" in available:
                return ToolCall(name="search_knowledge_base", arguments={"query": query})
            args: dict[str, Any] = {}
            if "symbol" in keys:
                m = _SYMBOL_RE.search(query)
                args["symbol"] = re.sub(r"\s+", "", m.group(0)).upper() if m else "NIFTY"
            if "strike" in keys:
                m = _STRIKE_RE.search(query)
                if m:
                    args["strike"] = float(m.group(1))
            if "expiry" in keys:
                m = _EXPIRY_RE.search(query)
                if m:
                    args["expiry"] = m.group(1)
            if "lots" in keys:
                m = _LOTS_RE.search(query)
                if m:
                    args["lots"] = int(m.group(1))
            if "position" in keys:
                is_option = re.search(r"\b(option|call|put|\bce\b|\bpe\b|premium)\b", query, re.IGNORECASE)
                short = _SIDE_RE.search(query)
                if is_option:
                    args["position"] = "option_sell" if short else "option_buy"
                else:
                    args["position"] = "futures_short" if short else "futures_long"
            if "query" in keys:
                args["query"] = query
            return ToolCall(name=tool, arguments=args)
        return None

    # -- synthesis ------------------------------------------------------
    def _summarise_tools(self, query: str, tool_results: list[Message]) -> str:
        lines = [f"Based on {len(tool_results)} tool result(s) for your question:"]
        for m in tool_results:
            body = m.content.strip()
            try:
                data = json.loads(body)
                body = self._flatten(data)
            except (json.JSONDecodeError, TypeError):
                pass
            lines.append(f"- {m.name or 'tool'}: {body[:800]}")
        lines.append(
            "This is market information for educational and testing purposes only, "
            "not investment advice."
        )
        return "\n".join(lines)

    @staticmethod
    def _flatten(data: Any, depth: int = 0) -> str:
        if depth > 3:
            return "..."
        if isinstance(data, dict):
            return "; ".join(f"{k}={StubLLM._flatten(v, depth + 1)}" for k, v in list(data.items())[:12])
        if isinstance(data, list):
            return " | ".join(StubLLM._flatten(v, depth + 1) for v in data[:4])
        text = str(data)
        return text[:400] + "..." if len(text) > 400 else text

    def _answer_from_context(self, query: str, system: str, messages: list[Message]) -> str:
        """Extractive synthesis: one best passage per context block.

        Handles both context shapes used in this application — RAG's
        `[doc KB-03 | section]` blocks and the supervisor's
        `[T1 | risk_analyst | completed]` specialist findings — so the same
        deterministic backend can drive all three applications.
        """
        blocks = re.findall(
            r"\[(?:doc|source|chunk|T\d+)\s[^\]]*\]\s*(.*?)(?=\n\[(?:doc|source|chunk|T\d+)\s|\Z)",
            system,
            re.S,
        )
        blocks = [b.strip() for b in blocks if b.strip()]
        if not blocks:
            blocks = [m.content for m in messages if m.role == "assistant" and m.content.strip()]
        if not blocks:
            return (
                "I could not find supporting material in the knowledge base for that question, "
                "so I am not able to answer it. Please rephrase or ask about NSE/SEBI derivatives topics "
                "covered by the corpus."
            )

        keywords = {w for w in re.findall(r"[a-z]{4,}", query.lower())}
        picked: list[str] = []
        for block in blocks[:5]:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", block) if len(s.strip()) > 15]
            if not sentences:
                continue
            scored = sorted(
                sentences,
                key=lambda s: -len(keywords & set(re.findall(r"[a-z]{4,}", s.lower()))),
            )
            best = scored[0]
            # Keep a second sentence when the block is substantive and on-topic.
            if len(scored) > 1 and keywords & set(re.findall(r"[a-z]{4,}", scored[1].lower())):
                best = f"{best} {scored[1]}"
            if best not in picked:
                picked.append(best)

        if not picked:
            return (
                "The retrieved documents do not contain enough information to answer that reliably. "
                "I am not going to guess."
            )
        return " ".join(picked)


# ----------------------------------------------------------------------------
def build_llm(cfg=None) -> BaseLLM:
    from ..config import get_config

    cfg = cfg or get_config().llm
    model = cfg.default_model()
    common = dict(
        model=model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        timeout_s=cfg.timeout_s,
    )
    provider = cfg.provider
    if provider == "openai":
        return OpenAILLM(api_key=cfg.openai_key, base_url=cfg.openai_base_url, **common)
    if provider == "anthropic":
        return AnthropicLLM(api_key=cfg.anthropic_key, **common)
    if provider == "ollama":
        return OllamaLLM(host=cfg.ollama_host, **common)
    return StubLLM(**common)
