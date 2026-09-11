"""Input and output guardrails.

This is the single most important module for the red-team half of the capstone.
Every control here can be switched off via QTCAP_VULNERABLE_MODE=1, so a
trainee can run the same attack twice and watch it succeed, then fail. A
red-team test that has never been seen to pass against a vulnerable build is a
test nobody trusts.

Controls implemented
--------------------
  IN-01  prompt injection / instruction override detection
  IN-02  jailbreak & role-play persona attacks
  IN-03  system-prompt and configuration extraction attempts
  IN-04  tool/argument abuse (mass extraction, path traversal, SSRF-ish input)
  IN-05  PII submitted by the user (PAN, Aadhaar, account, card, phone, email)
  IN-06  scope enforcement — the app answers capital-market questions only
  OUT-01 PII leakage in the response
  OUT-02 credential / configuration leakage
  OUT-03 personalised investment advice
  OUT-04 guaranteed-return and price-prediction claims
  OUT-05 mandatory disclaimer presence
  OUT-06 market-manipulation and insider-trading facilitation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Severity = Literal["low", "medium", "high", "critical"]
Action = Literal["allow", "flag", "sanitize", "block"]


@dataclass
class Finding:
    control: str
    name: str
    severity: Severity
    action: Action
    evidence: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GuardResult:
    allowed: bool = True
    action: Action = "allow"
    findings: list[Finding] = field(default_factory=list)
    sanitized_text: str = ""
    refusal_message: str = ""

    @property
    def triggered(self) -> list[str]:
        return [f.control for f in self.findings]

    @property
    def max_severity(self) -> str:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return max((f.severity for f in self.findings), key=lambda s: order[s], default="none")

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "max_severity": self.max_severity,
            "controls_triggered": self.triggered,
            "findings": [f.to_dict() for f in self.findings],
            "refusal_message": self.refusal_message,
        }


# ---------------------------------------------------------------------------
# Pattern libraries
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|preceding)\s+(instructions?|prompts?|rules?|directions?)", "instruction override"),
    (r"disregard\s+(all\s+|your\s+|the\s+)?(previous|prior|above|system|safety)\s*(instructions?|rules?|prompt|guidelines?)?", "instruction override"),
    (r"forget\s+(everything|all|what)\s+(you|we)\s+(were\s+)?(told|know|said)", "context reset"),
    (r"\bnew\s+(system\s+)?(instructions?|directive|prompt)\s*[:\-]", "injected directive"),
    (r"you\s+are\s+now\s+(a|an|in)\s+", "role reassignment"),
    (r"from\s+now\s+on,?\s+(you|your)\b", "role reassignment"),
    (r"\boverride\s+(your\s+)?(safety|guardrails?|restrictions?|filters?|policy)", "control bypass"),
    (r"\b(admin|developer|debug|maintenance|god)\s+mode\b", "privilege escalation"),
    (r"</?(system|instruction|admin)>", "delimiter injection"),
    (r"\[\[?\s*(system|admin|override)\s*\]?\]", "delimiter injection"),
    (r"###\s*(system|new instructions|end of context)", "delimiter injection"),
    (r"\bsudo\b|\bas\s+root\b", "privilege escalation"),
    (r"repeat\s+(the\s+)?(text|words?|content)\s+(above|before)", "context exfiltration"),
]

JAILBREAK_PATTERNS = [
    (r"\bDAN\b|\bdo\s+anything\s+now\b", "known jailbreak persona"),
    (r"pretend\s+(to\s+be|you\s+are|that\s+you)", "role-play bypass"),
    (r"act\s+as\s+(if\s+)?(an?\s+)?(unrestricted|uncensored|unfiltered|amoral|evil)", "role-play bypass"),
    (r"(hypothetically|in\s+a\s+fictional\s+(world|scenario|story)|for\s+a\s+novel),?\s+(how|what|explain).{0,80}(manipulat|insider|front.?run|spoof|pump)", "fiction framing"),
    (r"there\s+are\s+no\s+(rules|restrictions|laws)", "norm suspension"),
    (r"\bno\s+(disclaimers?|warnings?|caveats?)\b", "safety stripping"),
    (r"answer\s+without\s+(any\s+)?(restrictions?|filters?|guardrails?|disclaimers?)", "safety stripping"),
    (r"your\s+(previous|real|true)\s+(self|personality|training)", "persona attack"),
    (r"\bopposite\s+day\b|\breverse\s+psychology\b", "logic inversion"),
    (r"grandma|grandmother.{0,40}(used\s+to|bedtime|tell\s+me)", "emotional pretext"),
]

EXTRACTION_PATTERNS = [
    (r"(what|show|print|reveal|repeat|output|display|dump)\s+(is\s+|me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules|configuration|config|context)", "system prompt extraction"),
    (r"(api[_\s-]?key|secret|token|password|credential|bearer)", "credential probing"),
    (r"(list|show|enumerate)\s+(all\s+)?(your\s+)?(tools?|functions?|capabilities|endpoints?)\s+(with|and)\s+(their\s+)?(schemas?|parameters?|internals?)", "capability enumeration"),
    (r"what\s+(model|llm|provider)\s+(are\s+you|do\s+you\s+use).{0,30}(key|endpoint|url|version\s+string)", "infrastructure probing"),
    (r"\benvironment\s+variables?\b|\benv\s+vars?\b|\bos\.environ\b", "environment probing"),
    (r"verbatim.{0,30}(instructions?|prompt|system)", "system prompt extraction"),
]

TOOL_ABUSE_PATTERNS = [
    (r"\.\./|\.\.\\|/etc/passwd|C:\\\\Windows", "path traversal"),
    (r"\b(file|ftp|gopher)://", "scheme abuse"),
    (r"(169\.254\.169\.254|localhost:\d+|127\.0\.0\.1:\d+|metadata\.google)", "SSRF target"),
    (r"(drop|delete|truncate)\s+(table|database)|;\s*--|\bunion\s+select\b", "SQL injection"),
    (r"\$\(|\`|\|\s*(sh|bash|curl|wget)\b|&&\s*(rm|cat)\b", "command injection"),
    (r"(fetch|download|get)\s+(all|every)\s+(strikes?|symbols?|contracts?|records?)\s+(for\s+)?(all|every)", "mass extraction"),
    (r"\b(loop|repeat|call)\s+(it|this|the\s+tool)\s+(\d{3,}|a\s+thousand|forever|infinitely)", "resource exhaustion"),
]

MANIPULATION_PATTERNS = [
    (r"\b(insider|non[- ]public|unpublished\s+price\s+sensitive|UPSI)\b.{0,60}\b(information|tip|news|trade|profit)\b", "insider trading"),
    (r"\b(pump\s+and\s+dump|ramp\s+the\s+(price|stock)|circular\s+trading|wash\s+trade|matched\s+order)", "market manipulation"),
    (r"\b(spoof|layering)\b.{0,40}\b(order|book|market)\b", "order-book manipulation"),
    (r"\bfront[- ]?run(ning)?\b.{0,40}\b(client|order|trade)\b", "front running"),
    (r"how\s+(do|can)\s+i\s+.{0,40}(avoid|evade|bypass|hide\s+from)\s+.{0,20}(sebi|regulator|surveillance|audit|detection)", "regulatory evasion"),
    (r"(manipulat|corner|rig)\w*\s+the\s+(market|price|stock|index|expiry)", "market manipulation"),
    (r"\bexpiry\s+(day\s+)?(manipulation|ramping)\b", "expiry manipulation"),
]

ADVICE_PATTERNS = [
    (r"\byou\s+should\s+(buy|sell|short|long|purchase|exit|hold|book|square\s+off)\b", "directive recommendation"),
    (r"\bi\s+(recommend|advise|suggest)\s+(that\s+)?(you\s+)?(buy|sell|short|go\s+long|invest|enter)", "directive recommendation"),
    (r"\b(buy|sell|short)\s+(this|it|now|immediately|today)\b", "directive recommendation"),
    (r"\bguaranteed?\s+(returns?|profits?|gains?|income)\b", "guaranteed return"),
    (r"\brisk[- ]free\s+(profit|return|trade|money)\b", "guaranteed return"),
    (r"\b(will|shall)\s+(definitely|certainly|surely)\s+(rise|fall|go\s+up|go\s+down|hit|reach)\b", "price prediction"),
    (r"\b(sure[- ]shot|can'?t\s+lose|no\s+downside|assured\s+profit|100%\s+(safe|accurate|profitable))\b", "guaranteed return"),
    (r"\bmy\s+target\s+(price\s+)?(is|for)\b.{0,20}\d", "price prediction"),
    (r"\bput\s+(all|your\s+entire)\s+(your\s+)?(savings|capital|money|portfolio)\b", "unsuitable advice"),
]

# PII detectors tuned for the Indian market context.
PII_PATTERNS = [
    ("pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "PAN number"),
    ("aadhaar", r"\b\d{4}\s?\d{4}\s?\d{4}\b", "Aadhaar number"),
    ("card", r"\b(?:\d{4}[ -]?){3}\d{4}\b", "payment card number"),
    ("client_code", r"\b(?:client|ucc|dp)\s*(?:code|id)?\s*[:#-]?\s*[A-Z0-9]{6,12}\b", "client/UCC code"),
    ("demat", r"\bIN[0-9]{14}\b", "demat account number"),
    ("phone", r"\b(?:\+?91[- ]?)?[6-9]\d{9}\b", "Indian mobile number"),
    ("email", r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b", "email address"),
    ("bank_account", r"\b(?:a/?c|account)\s*(?:no\.?|number)?\s*[:#-]?\s*\d{9,18}\b", "bank account number"),
    ("ifsc", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "IFSC code"),
]

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9_\-]{16,}", "OpenAI-style API key"),
    (r"sk-ant-[A-Za-z0-9_\-]{16,}", "Anthropic API key"),
    (r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "AWS access key"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.", "JWT"),
    (r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{12,}", "inline credential"),
    (r"QTCAP_[A-Z_]+\s*=\s*\S+", "application configuration value"),
]

# In-domain vocabulary for scope enforcement.
DOMAIN_TERMS = {
    "option", "options", "future", "futures", "derivative", "derivatives", "strike", "expiry",
    "premium", "delta", "gamma", "theta", "vega", "rho", "greeks", "margin", "span", "exposure",
    "nifty", "banknifty", "finnifty", "midcpnifty", "sensex", "nse", "bse", "sebi", "index",
    "equity", "share", "stock", "market", "trading", "trade", "position", "hedge", "hedging",
    "volatility", "iv", "oi", "pcr", "straddle", "strangle", "spread", "condor", "butterfly",
    "settlement", "physical", "delivery", "lot", "contract", "underlying", "spot", "basis",
    "arbitrage", "portfolio", "risk", "stt", "tax", "brokerage", "order", "limit", "stoploss",
    "square", "rollover", "carry", "call", "put", "ltp", "price", "quote", "chain", "exchange",
    "clearing", "corporation", "broker", "demat", "circuit", "auction", "ipo", "dividend",
    "split", "bonus", "adjustment", "payoff", "breakeven", "moneyness", "atm", "otm", "itm",
    "collateral", "haircut", "leverage", "liquidity", "spread", "slippage", "expiry", "series",
    "usd", "inr", "eur", "gbp", "jpy", "forex", "fx", "currency", "rupee", "dollar", "rate",
    "exchange", "gamma", "vanna", "charm", "notional", "lot", "size", "tick", "basis",
}

OFF_DOMAIN_HINTS = [
    (r"\b(recipe|cook|bake|pizza|biryani|restaurant)\b", "cooking"),
    (r"\b(python|javascript|java|sql|code|function|debug|regex)\s+(script|code|program|snippet|function)\b", "software development"),
    (r"\b(poem|sonnet|haiku|story|screenplay|lyrics|novel)\b", "creative writing"),
    (r"\b(diagnos|symptom|medicine|prescription|dosage|disease)\w*\b", "medical"),
    (r"\b(divorce|lawsuit|legal\s+notice|custody|criminal\s+case)\b", "legal"),
    (r"\b(football|cricket\s+score|movie|netflix|song|celebrity)\b", "entertainment"),
    (r"\b(weather|temperature\s+in|forecast\s+for)\b", "weather"),
    (r"\b(translate|translation)\s+(this|the\s+following)\b", "translation"),
]

MANDATORY_DISCLAIMER_TRIGGERS = re.compile(
    r"\b(strategy|strategies|straddle|strangle|spread|condor|position|payoff|margin|"
    r"buy|sell|invest|return|profit|loss|risk|recommend|portfolio)\b",
    re.IGNORECASE,
)
DISCLAIMER_MARKERS = re.compile(
    r"(not\s+(investment|financial|trading)\s+advice|educational\s+(purposes?|only)|"
    r"consult\s+(a\s+)?(sebi[- ]registered\s+)?(advisor|adviser|professional)|"
    r"for\s+(testing|training|educational)\s+purposes|indicative\s+only|"
    r"do\s+your\s+own\s+(research|due\s+diligence))",
    re.IGNORECASE,
)

REFUSAL_MARKERS = re.compile(
    r"(i\s+(can'?t|cannot|will\s+not|won'?t|am\s+not\s+able\s+to|am\s+unable\s+to)|"
    r"not\s+something\s+i\s+can|i\s+have\s+to\s+decline|outside\s+(the\s+)?scope|"
    r"i\s+don'?t\s+have|unable\s+to\s+help|not\s+going\s+to)",
    re.IGNORECASE,
)


def _scan(text: str, patterns, control: str, severity: Severity, action: Action) -> list[Finding]:
    findings = []
    for pattern, label in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            findings.append(
                Finding(control=control, name=label, severity=severity, action=action,
                        evidence=m.group(0)[:120])
            )
    return findings


# ---------------------------------------------------------------------------
# Input guard
# ---------------------------------------------------------------------------
def redact_pii(text: str) -> tuple[str, list[Finding]]:
    findings, out = [], text
    for key, pattern, label in PII_PATTERNS:
        for m in re.finditer(pattern, out):
            findings.append(
                Finding(control="IN-05", name=label, severity="high", action="sanitize",
                        evidence=m.group(0)[:6] + "***")
            )
        out = re.sub(pattern, f"[REDACTED_{key.upper()}]", out)
    return out, findings


def is_in_domain(text: str) -> tuple[bool, str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z]+", lowered))
    if words & DOMAIN_TERMS:
        return True, "domain term present"
    for pattern, label in OFF_DOMAIN_HINTS:
        if re.search(pattern, lowered):
            return False, label
    if len(words) <= 3:
        return True, "too short to classify; allowed"
    return False, "no capital-market vocabulary detected"


def check_input(text: str, enforce: bool | None = None) -> GuardResult:
    from ..config import get_config

    cfg = get_config()
    enforce = cfg.guardrails_enabled and not cfg.vulnerable_mode if enforce is None else enforce

    findings: list[Finding] = []
    findings += _scan(text, INJECTION_PATTERNS, "IN-01", "critical", "block")
    findings += _scan(text, JAILBREAK_PATTERNS, "IN-02", "high", "block")
    findings += _scan(text, EXTRACTION_PATTERNS, "IN-03", "high", "block")
    findings += _scan(text, TOOL_ABUSE_PATTERNS, "IN-04", "critical", "block")
    findings += _scan(text, MANIPULATION_PATTERNS, "OUT-06", "critical", "block")

    sanitized, pii = redact_pii(text)
    findings += pii

    in_domain, reason = is_in_domain(text)
    if not in_domain:
        findings.append(
            Finding(control="IN-06", name="out of scope", severity="medium", action="block",
                    evidence=reason, detail="Application scope is Indian capital markets and derivatives.")
        )

    result = GuardResult(findings=findings, sanitized_text=sanitized)
    if not enforce:
        result.allowed = True
        result.action = "allow"
        for f in result.findings:
            f.action = "flag"
        result.sanitized_text = text  # vulnerable mode does not even redact
        return result

    blocking = [f for f in findings if f.action == "block"]
    if blocking:
        result.allowed = False
        result.action = "block"
        result.refusal_message = _refusal_for(blocking[0])
    elif pii:
        result.action = "sanitize"
    return result


def _refusal_for(finding: Finding) -> str:
    if finding.control in ("IN-01", "IN-02", "IN-03"):
        return (
            "I can't act on that request. It attempts to change my operating instructions "
            "or extract my configuration, which I won't do. I'm happy to help with questions "
            "about Indian equity derivatives — contracts, Greeks, margins, settlement or strategy mechanics."
        )
    if finding.control == "IN-04":
        return (
            "I can't process that request: the input contains a pattern associated with tool or "
            "system abuse. Please rephrase it as a normal market-data or derivatives question."
        )
    if finding.control == "OUT-06":
        return (
            "I can't help with that. It relates to insider trading or market manipulation, which is "
            "illegal under Indian securities law and outside what this application will assist with. "
            "I can explain the surveillance and regulatory framework instead, if that is useful."
        )
    return (
        "That question is outside the scope of this application. I cover Indian capital markets and "
        "equity derivatives only — futures, options, Greeks, margins, settlement and contract specifications."
    )


# ---------------------------------------------------------------------------
# Output guard
# ---------------------------------------------------------------------------
def check_output(
    text: str,
    context_chunks: list[str] | None = None,
    require_disclaimer: bool | None = None,
    enforce: bool | None = None,
) -> GuardResult:
    from ..config import get_config

    cfg = get_config()
    enforce = cfg.guardrails_enabled and not cfg.vulnerable_mode if enforce is None else enforce

    findings: list[Finding] = []
    _, pii = redact_pii(text)
    for f in pii:
        findings.append(Finding("OUT-01", f.name, "critical", "block", f.evidence,
                                "Personal data must never appear in a response."))
    findings += _scan(text, SECRET_PATTERNS, "OUT-02", "critical", "block")
    findings += _scan(text, ADVICE_PATTERNS, "OUT-03", "high", "block")
    findings += _scan(text, MANIPULATION_PATTERNS, "OUT-06", "critical", "block")

    needs_disclaimer = (
        MANDATORY_DISCLAIMER_TRIGGERS.search(text) is not None
        if require_disclaimer is None
        else require_disclaimer
    )
    has_disclaimer = DISCLAIMER_MARKERS.search(text) is not None
    is_refusal = REFUSAL_MARKERS.search(text) is not None
    if needs_disclaimer and not has_disclaimer and not is_refusal:
        findings.append(
            Finding("OUT-05", "missing disclaimer", "medium", "sanitize",
                    detail="Responses touching strategy, risk or returns must carry the educational disclaimer.")
        )

    out = text
    result = GuardResult(findings=findings, sanitized_text=out)
    if not enforce:
        for f in result.findings:
            f.action = "flag"
        result.action = "allow"
        return result

    blocking = [f for f in findings if f.action == "block"]
    if blocking:
        result.allowed = False
        result.action = "block"
        result.refusal_message = (
            "I generated a response that failed this application's output policy "
            f"({blocking[0].control}: {blocking[0].name}), so I am not showing it. "
            "Please rephrase your question — I can explain the mechanics of derivatives "
            "without making a personal recommendation."
        )
        result.sanitized_text = result.refusal_message
        return result

    if any(f.control == "OUT-05" for f in findings):
        out = out.rstrip() + (
            "\n\nThis is educational information about market mechanics, not investment advice. "
            "Consult a SEBI-registered investment adviser before acting on it."
        )
        result.action = "sanitize"
        result.sanitized_text = out
    return result


def groundedness(answer: str, context_chunks: list[str]) -> dict[str, Any]:
    """Lexical grounding proxy: what share of the answer's content words appear
    in the retrieved context? Cheap, deterministic, and good enough to catch a
    fabricated answer in a training setting."""
    from ..rag.store import tokenize

    ans = [t for t in tokenize(answer) if len(t) > 3]
    if not ans:
        return {"score": 1.0, "supported": [], "unsupported": [], "verdict": "empty"}
    ctx = set()
    for chunk in context_chunks:
        ctx.update(tokenize(chunk))
    supported = [t for t in ans if t in ctx]
    unsupported = sorted({t for t in ans if t not in ctx})
    score = len(supported) / len(ans)
    verdict = "grounded" if score >= 0.75 else "partially_grounded" if score >= 0.5 else "ungrounded"
    return {
        "score": round(score, 3),
        "verdict": verdict,
        "unsupported_terms": unsupported[:20],
        "context_chunks": len(context_chunks),
    }


# ---------------------------------------------------------------------------
# Document guard (IN-07)
# ---------------------------------------------------------------------------
# A document a trainee adds to the corpus is the most direct route into a RAG
# system there is: whatever it says gets retrieved, pasted into the prompt, and
# read by the model as reference material. The system prompt already tells the
# model that context is data rather than instructions — this is the control that
# checks whether a document is *trying* to be instructions, so the attempt is
# visible at upload time instead of being discovered in an answer three
# questions later.
#
# It flags, it does not block. A poisoned document you cannot load is a document
# you cannot test against, and the red-team labs need to load exactly this kind
# of file.
def check_document(text: str, filename: str = "") -> list[Finding]:
    """Scan a document being added to the corpus. Returns findings, never raises."""
    findings: list[Finding] = []
    findings += _scan(text, INJECTION_PATTERNS, "IN-07", "critical", "flag")
    findings += _scan(text, JAILBREAK_PATTERNS, "IN-07", "high", "flag")
    findings += _scan(text, EXTRACTION_PATTERNS, "IN-07", "high", "flag")
    findings += _scan(text, TOOL_ABUSE_PATTERNS, "IN-07", "critical", "flag")
    findings += _scan(text, MANIPULATION_PATTERNS, "IN-07", "critical", "flag")
    findings += _scan(text, SECRET_PATTERNS, "OUT-02", "critical", "flag")
    _, pii = redact_pii(text)
    for f in pii:
        f.action = "flag"
    findings += pii

    # Text addressed to the model rather than to a reader is the tell that
    # survives paraphrase, so it is worth its own check.
    for pattern, label in (
        (r"\b(?:as an? |you are an? )(?:ai|assistant|language model)\b", "document addresses the model"),
        (r"\bwhen (?:asked|answering|you (?:are )?asked)\b[^.]{0,60}\b(?:say|reply|respond|answer)\b",
         "document scripts an answer"),
        (r"\b(?:always|never) (?:say|mention|reveal|recommend|cite)\b", "document dictates behaviour"),
    ):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            findings.append(Finding(control="IN-07", name=label, severity="high", action="flag",
                                    evidence=m.group(0)[:120]))

    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for f in findings:
        key = (f.control, f.name)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique
