"""Defect log: what a trainee files when they find something.

A testing course that stops at a pass/fail number teaches half the job. The
other half is writing the finding down so somebody can act on it, and getting it
in front of them. This module is the smallest thing that does both:

  * an append-only JSONL store, so nothing is lost and nothing needs a database
  * a `from_failure` constructor that turns a failing test case into a draft
    finding, pre-filled with the reproduction
  * export to Markdown, CSV and JSON for a report or a ticket system
  * optional outbound notification to a webhook (Slack, Teams, Discord or any
    JSON endpoint), configured by the operator, never by a student

Storage is a file, which is right for a training instance and wrong for
production — say so out loud rather than pretending otherwise. On a free hosting
tier with an ephemeral filesystem the log resets when the instance restarts, so
the UI pushes students to export.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR

ISSUES_PATH = DATA_DIR / "issues.jsonl"
MAX_ISSUES = 2000

SEVERITIES = ("critical", "high", "medium", "low")
STATUSES = ("open", "triaged", "confirmed", "rejected", "fixed")
AREAS = (
    "rag_retrieval", "rag_grounding", "citations", "tool_selection", "tool_contract",
    "agent_control_flow", "mcp_routing", "multi_agent", "guardrail_input",
    "guardrail_output", "market_data", "pricing_math", "ui", "performance", "other",
)

_SECRET_RE = re.compile(
    r"\b(gsk_[A-Za-z0-9_\-]{10,}|sk-ant-[A-Za-z0-9_\-]{10,}|sk-or-[A-Za-z0-9_\-]{10,}"
    r"|sk-[A-Za-z0-9_\-]{16,}|csk-[A-Za-z0-9_\-]{10,}|xai-[A-Za-z0-9_\-]{10,}"
    r"|AIza[A-Za-z0-9_\-]{20,})\b"
)
# Students paste raw request bodies into findings; strip anything credential-shaped
# before it is written to a shared log.
_PII_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z]|\d{4}\s?\d{4}\s?\d{4}|(?:\d{4}[ -]?){3}\d{4})\b")


def _clean(text: Any, limit: int = 4000) -> str:
    out = _SECRET_RE.sub("[REDACTED_KEY]", str(text or ""))
    out = _PII_RE.sub("[REDACTED_PII]", out)
    return out[:limit]


@dataclass
class Issue:
    id: str
    title: str
    area: str = "other"
    severity: str = "medium"
    status: str = "open"
    summary: str = ""
    steps: str = ""
    expected: str = ""
    actual: str = ""
    impact: str = ""
    case_id: str = ""
    provider: str = ""
    model: str = ""
    reporter: str = ""
    created_at: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _validate(value: str, allowed: tuple[str, ...], default: str) -> str:
    v = (value or "").strip().lower()
    return v if v in allowed else default


def create_issue(payload: dict[str, Any]) -> Issue:
    title = _clean(payload.get("title"), 200).strip()
    if not title:
        raise ValueError("An issue needs a title.")
    issue = Issue(
        id=f"QT-{uuid.uuid4().hex[:6].upper()}",
        title=title,
        area=_validate(payload.get("area", ""), AREAS, "other"),
        severity=_validate(payload.get("severity", ""), SEVERITIES, "medium"),
        status=_validate(payload.get("status", ""), STATUSES, "open"),
        summary=_clean(payload.get("summary"), 2000),
        steps=_clean(payload.get("steps"), 4000),
        expected=_clean(payload.get("expected"), 2000),
        actual=_clean(payload.get("actual"), 4000),
        impact=_clean(payload.get("impact"), 1000),
        case_id=_clean(payload.get("case_id"), 60),
        provider=_clean(payload.get("provider"), 40),
        model=_clean(payload.get("model"), 80),
        reporter=_clean(payload.get("reporter"), 60) or "anonymous",
        created_at=_now(),
        tags=[_clean(t, 30) for t in (payload.get("tags") or [])][:8],
    )
    _append(issue)
    notify(issue)
    return issue


def from_failure(result: dict[str, Any], reporter: str = "", provider: str = "", model: str = "") -> dict[str, Any]:
    """Turn a failing test result into a pre-filled draft finding.

    Returned as a draft rather than saved, because a finding nobody reviewed is
    noise. The student edits the impact line before filing — which is the part
    that turns a symptom into something a stakeholder can act on.
    """
    reasons = [f"{c['type']}: {c['message']}" for c in result.get("checks", []) if not c.get("passed")]
    if not reasons and result.get("error"):
        reasons = [str(result["error"])]
    inp = result.get("input") or {}
    return {
        "title": f"{result.get('id', 'case')} — {result.get('title', 'test failure')}"[:200],
        "area": result.get("category", "other") if result.get("category") in AREAS else "other",
        "severity": _validate(result.get("severity", ""), SEVERITIES, "medium"),
        "case_id": result.get("id", ""),
        "summary": f"Case {result.get('id')} failed against target '{result.get('target')}'.",
        "steps": json.dumps(inp, indent=2)[:3000],
        "expected": "\n".join(
            f"{c['type']}({', '.join(f'{k}={v}' for k, v in c.get('params', {}).items())})"
            for c in result.get("checks", []) if not c.get("passed")
        )[:2000],
        "actual": "\n".join(reasons)[:3000],
        "impact": "",
        "provider": provider,
        "model": model,
        "reporter": reporter,
        "tags": ["from-suite", result.get("suite", "")],
    }


def _append(issue: Issue) -> None:
    try:
        ISSUES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ISSUES_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(issue.to_dict()) + "\n")
    except OSError:
        pass  # a training log is best-effort; never break the UI over it


def list_issues(status: str | None = None, severity: str | None = None,
                area: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    if not ISSUES_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        with ISSUES_PATH.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    # Later records for the same id win, so an update supersedes the original.
    merged: dict[str, dict] = {}
    for rec in out:
        merged[rec.get("id", uuid.uuid4().hex)] = rec
    rows = sorted(merged.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if severity:
        rows = [r for r in rows if r.get("severity") == severity]
    if area:
        rows = [r for r in rows if r.get("area") == area]
    return rows[:limit]


def update_issue(issue_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    rows = list_issues(limit=MAX_ISSUES)
    current = next((r for r in rows if r.get("id") == issue_id), None)
    if current is None:
        return None
    updated = dict(current)
    if "status" in changes:
        updated["status"] = _validate(changes["status"], STATUSES, updated.get("status", "open"))
    if "severity" in changes:
        updated["severity"] = _validate(changes["severity"], SEVERITIES, updated.get("severity", "medium"))
    for key in ("impact", "summary", "actual", "expected", "steps", "title"):
        if key in changes:
            updated[key] = _clean(changes[key])
    _append(Issue(**{k: updated.get(k, "") if k != "tags" else updated.get("tags", [])
                     for k in Issue.__dataclass_fields__}))
    return updated


def stats() -> dict[str, Any]:
    rows = list_issues(limit=MAX_ISSUES)
    by = lambda key: {  # noqa: E731
        v: sum(1 for r in rows if r.get(key) == v)
        for v in sorted({r.get(key, "") for r in rows} - {""})
    }
    return {
        "total": len(rows),
        "open": sum(1 for r in rows if r.get("status") == "open"),
        "critical_open": sum(1 for r in rows if r.get("status") == "open" and r.get("severity") == "critical"),
        "by_severity": by("severity"),
        "by_area": by("area"),
        "by_status": by("status"),
        "storage": str(ISSUES_PATH),
        "ephemeral_warning": (
            "Findings are stored in a file on this instance. On a free hosting tier that "
            "filesystem is wiped when the container restarts — export before you finish."
        ),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def to_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "# Findings\n\nNo issues recorded.\n"
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rows = sorted(rows, key=lambda r: order.get(r.get("severity", "medium"), 9))
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.get("severity", "medium")] = counts.get(r.get("severity", "medium"), 0) + 1

    out = [
        "# Findings — Capital Markets Agentic Capstone",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')} · "
        f"{len(rows)} finding(s): " + ", ".join(f"{v} {k}" for k, v in counts.items()),
        "",
    ]
    for r in rows:
        out += [
            f"## {r.get('id')} — {r.get('title')}",
            "",
            f"**Severity** {r.get('severity')} · **Area** {r.get('area')} · "
            f"**Status** {r.get('status')} · **Reported by** {r.get('reporter')}"
            + (f" · **Case** `{r.get('case_id')}`" if r.get("case_id") else "")
            + (f" · **Backend** {r.get('provider')}/{r.get('model')}" if r.get("provider") else ""),
            "",
        ]
        if r.get("summary"):
            out += [r["summary"], ""]
        if r.get("steps"):
            out += ["**Reproduction**", "", "```json", r["steps"], "```", ""]
        if r.get("expected"):
            out += ["**Expected**", "", r["expected"], ""]
        if r.get("actual"):
            out += ["**Actual**", "", r["actual"], ""]
        if r.get("impact"):
            out += ["**Business impact**", "", r["impact"], ""]
        out.append("---")
        out.append("")
    return "\n".join(out)


def to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    cols = ["id", "title", "area", "severity", "status", "case_id", "provider", "model",
            "reporter", "created_at", "summary", "expected", "actual", "impact"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
def notify(issue: Issue) -> dict[str, Any]:
    """Post a new finding to the operator's webhook, if one is configured.

    Configured by the person running the instance via QTCAP_NOTIFY_WEBHOOK —
    never by a student, since an attacker-supplied URL would make this an
    outbound request forwarder. Only fires at or above QTCAP_NOTIFY_MIN_SEVERITY
    (default: high), so a class filing twenty medium findings does not flood a
    channel.
    """
    url = os.environ.get("QTCAP_NOTIFY_WEBHOOK", "").strip()
    if not url or not url.startswith("https://"):
        return {"sent": False, "reason": "no webhook configured"}

    threshold = os.environ.get("QTCAP_NOTIFY_MIN_SEVERITY", "high").strip().lower()
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if order.get(issue.severity, 1) < order.get(threshold, 2):
        return {"sent": False, "reason": f"severity below threshold '{threshold}'"}

    text = (
        f"*{issue.severity.upper()}* finding filed — {issue.id}\n"
        f"*{issue.title}*\n"
        f"Area: {issue.area} · Reporter: {issue.reporter}"
        + (f" · Case: {issue.case_id}" if issue.case_id else "")
        + (f"\nImpact: {issue.impact}" if issue.impact else "")
    )
    # Slack, Teams and Discord each read a different field; send all three.
    body = {"text": text, "content": text,
            "summary": f"{issue.severity.upper()} — {issue.title}"}
    try:
        import httpx

        r = httpx.post(url, json=body, timeout=6.0)
        return {"sent": r.status_code < 400, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001 - notification must never break filing
        return {"sent": False, "reason": f"{type(exc).__name__}: {exc}"}
