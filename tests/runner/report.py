"""Renders the suite results as a self-contained HTML report plus JSON.

The HTML report is the artefact a trainee hands to a stakeholder: pass rate,
breakdown by category and severity, and — for every failure — the exact check
that failed and the application's actual output.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..runner.harness import summarise

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports"

CSS = """
:root{--bg:#f6f7f9;--surface:#fff;--border:#d8dde5;--text:#16202c;--muted:#5d6b7c;
--ok:#157347;--ok-soft:#e3f5eb;--bad:#b02a37;--bad-soft:#fdeaec;--warn:#9a6700;--warn-soft:#fff5d9;
--accent:#0b5ed7;--mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{background:var(--surface);border-bottom:1px solid var(--border);padding:18px 24px}
h1{font-size:18px;margin:0 0 4px}h2{font-size:15px;margin:26px 0 10px}
.sub{color:var(--muted);font-size:12.5px;margin:0}
main{max-width:1180px;margin:0 auto;padding:20px 24px 48px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px}
.card .n{font-size:26px;font-weight:700;line-height:1.1}
.card .l{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.card.ok .n{color:var(--ok)}.card.bad .n{color:var(--bad)}
.bar{height:9px;border-radius:5px;background:var(--bad-soft);overflow:hidden;margin-top:8px}
.bar>span{display:block;height:100%;background:var(--ok)}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden;font-size:13px}
th,td{padding:7px 11px;text-align:left;border-bottom:1px solid var(--border)}
thead th{background:#f0f2f5;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.04em}
td.num,th.num{text-align:right;font-family:var(--mono)}
tr:last-child td{border-bottom:none}
.tag{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;font-family:var(--mono)}
.pass{background:var(--ok-soft);color:var(--ok)}.fail{background:var(--bad-soft);color:var(--bad)}
.sev-critical{background:var(--bad-soft);color:var(--bad)}.sev-high{background:var(--warn-soft);color:var(--warn)}
.sev-medium{background:#eef2f7;color:var(--muted)}.sev-low{background:#eef2f7;color:var(--muted)}
.failure{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--bad);border-radius:8px;padding:12px 14px;margin-bottom:10px}
.failure h3{margin:0 0 6px;font-size:13.5px}
.failure ul{margin:6px 0 0;padding-left:18px;font-family:var(--mono);font-size:12px;color:var(--bad)}
.out{background:#0f1720;color:#d6e2f0;padding:9px 11px;border-radius:6px;font-family:var(--mono);font-size:11.5px;white-space:pre-wrap;margin-top:8px;max-height:190px;overflow:auto}
footer{color:var(--muted);font-size:12px;padding:16px 24px;border-top:1px solid var(--border);background:var(--surface)}
@media(max-width:700px){main{padding:16px}th,td{padding:6px 8px}}
"""


def _rows(bucket: dict[str, dict[str, int]], label: str) -> str:
    out = []
    for key, v in sorted(bucket.items(), key=lambda kv: (kv[1]["passed"] == kv[1]["total"], kv[0])):
        rate = round(v["passed"] / v["total"] * 100) if v["total"] else 0
        cls = "pass" if v["passed"] == v["total"] else "fail"
        out.append(
            f"<tr><td>{html.escape(key)}</td><td class='num'>{v['total']}</td>"
            f"<td class='num'>{v['passed']}</td><td class='num'>{v['total'] - v['passed']}</td>"
            f"<td class='num'><span class='tag {cls}'>{rate}%</span></td></tr>"
        )
    return (
        f"<h2>{label}</h2><table><thead><tr><th>{label}</th><th class='num'>Total</th>"
        f"<th class='num'>Passed</th><th class='num'>Failed</th><th class='num'>Rate</th>"
        f"</tr></thead><tbody>{''.join(out)}</tbody></table>"
    )


def render_html(results: list[dict]) -> str:
    s = summarise(results)
    blue = [r for r in results if r["suite"] == "blue"]
    red = [r for r in results if r["suite"] == "red"]
    blue_pass = sum(1 for r in blue if r["passed"])
    red_pass = sum(1 for r in red if r["passed"])

    failures = []
    for r in results:
        if r["passed"]:
            continue
        reasons = "".join(
            f"<li>{html.escape(c['type'])}: {html.escape(str(c['message']))}</li>"
            for c in r["checks"] if not c["passed"]
        ) or f"<li>{html.escape(str(r.get('error') or 'unknown'))}</li>"
        answer = str((r.get("result") or {}).get("answer", ""))[:900]
        out_block = f"<div class='out'>{html.escape(answer)}</div>" if answer else ""
        failures.append(
            f"<div class='failure'><h3>{html.escape(r['id'])} — {html.escape(r['title'])}"
            f" <span class='tag sev-{html.escape(r['severity'])}'>{html.escape(r['severity'])}</span></h3>"
            f"<div class='sub'>{html.escape(r['suite'])} · {html.escape(r['category'])} · "
            f"target {html.escape(r['target'])} · {r['duration_ms']}ms</div>"
            f"<ul>{reasons}</ul>{out_block}</div>"
        )

    failures_html = (
        "<h2>Failures</h2>" + "".join(failures)
        if failures
        else "<h2>Failures</h2><div class='card ok'><div class='n'>0</div>"
             "<div class='l'>every case passed</div></div>"
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QT Capstone — Test Report</title><style>{CSS}</style></head><body>
<header>
  <h1>Capital Markets Agentic Capstone — Test Report</h1>
  <p class="sub">Generated {datetime.now().strftime('%d %b %Y, %H:%M')} ·
     {s['total']} cases · {round(s['total_duration_ms'] / 1000, 1)}s</p>
</header>
<main>
  <div class="cards">
    <div class="card {'ok' if s['failed'] == 0 else 'bad'}">
      <div class="n">{s['pass_rate']}%</div><div class="l">pass rate</div>
      <div class="bar"><span style="width:{s['pass_rate']}%"></span></div>
    </div>
    <div class="card"><div class="n">{s['total']}</div><div class="l">total cases</div></div>
    <div class="card ok"><div class="n">{s['passed']}</div><div class="l">passed</div></div>
    <div class="card {'bad' if s['failed'] else ''}"><div class="n">{s['failed']}</div><div class="l">failed</div></div>
    <div class="card"><div class="n">{blue_pass}/{len(blue)}</div><div class="l">blue team</div></div>
    <div class="card"><div class="n">{red_pass}/{len(red)}</div><div class="l">red team</div></div>
  </div>
  {_rows(s['by_severity'], 'Severity')}
  {_rows(s['by_category'], 'Category')}
  {failures_html}
</main>
<footer>Quality Thought — training artefact. Market figures are educational, not investment advice.</footer>
</body></html>"""


def write_reports(results: list[dict], directory: Path | None = None) -> dict[str, Path]:
    directory = directory or REPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    html_path = directory / "test-report.html"
    json_path = directory / "test-report.json"
    html_path.write_text(render_html(results), encoding="utf-8")
    json_path.write_text(
        json.dumps({"summary": summarise(results), "results": results}, indent=2, default=str),
        encoding="utf-8",
    )
    return {"html": html_path, "json": json_path}
