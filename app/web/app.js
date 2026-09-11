/* QT Capital Markets Agentic Capstone — UI.
   Every result region carries a data-testid and a data-state attribute so UI
   automation can assert on state without scraping prose. */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------------- backend settings (bring your own key) ----------------
   The key lives in this browser's localStorage and is attached as a header on
   each request. It is never sent to any host but this application's own API,
   and the server never writes it anywhere. Wrapped in try/catch because
   storage throws in private windows and preview frames. */
const BK = "qtcap.backend";
let BACKEND = { provider: "stub", model: "", key: "" };
try {
  const saved = JSON.parse(localStorage.getItem(BK) || "null");
  if (saved && typeof saved === "object") BACKEND = { ...BACKEND, ...saved };
} catch { /* storage unavailable — carry on with the offline stub */ }

function saveBackend() {
  try { localStorage.setItem(BK, JSON.stringify(BACKEND)); } catch { /* ignore */ }
}

function backendHeaders() {
  const h = { "X-LLM-Provider": BACKEND.provider || "stub" };
  if (BACKEND.model) h["X-LLM-Model"] = BACKEND.model;
  if (BACKEND.key) h["X-LLM-Key"] = BACKEND.key;
  return h;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...backendHeaders() },
    ...options,
  });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); } catch { body = { raw: text }; }
  if (!res.ok && !body.error && !body.detail) body.detail = `HTTP ${res.status}`;
  return { status: res.status, body, latency: res.headers.get("X-Response-Time-Ms") };
}

/* ---------------- tabs ---------------- */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $(`panel-${tab.dataset.panel}`).classList.add("active");
  });
});

document.querySelectorAll(".examples").forEach((box) => {
  box.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip")) $(box.dataset.target).value = e.target.textContent;
  });
});

/* ---------------- shared renderers ---------------- */
function metric(label, value, tone = "") {
  return `<span class="metric ${tone}">${esc(label)}: ${esc(value)}</span>`;
}

function renderTrace(el, trace) {
  el.innerHTML = (trace || []).map((s) => {
    const bad = ["blocked", "error", "ungrounded", "denied", "empty"].includes(s.status);
    const warn = ["sanitize", "partially_grounded", "fallback", "tool_error"].includes(s.status);
    const detail = Object.entries(s.detail || {})
      .filter(([, v]) => v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && !v.length))
      .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join(",") : typeof v === "object" ? JSON.stringify(v) : v}`)
      .join(" · ");
    return `<div class="step ${bad ? "bad" : warn ? "warn" : "ok"}" data-stage="${esc(s.stage)}" data-status="${esc(s.status)}">
      <span class="st-name">${esc(s.stage)} → ${esc(s.status)}</span>
      <span class="step-detail">${esc(detail)} · ${s.duration_ms}ms</span></div>`;
  }).join("") || '<div class="step">no trace</div>';
}

function renderToolCalls(el, calls, kind = "tool") {
  el.innerHTML = (calls || []).map((c) => `
    <div class="tc" data-tool="${esc(c.tool)}" data-ok="${c.ok}">
      <div class="tc-head">
        <span class="ctx-doc">${esc(c.tool)}</span>
        <span>${c.server ? esc(c.server) + " · " : ""}${c.ok ? "ok" : "FAILED"} · ${c.duration_ms}ms</span>
      </div>
      <div class="ctx-body">args: ${esc(JSON.stringify(c.arguments))}${
        c.ok ? "" : `<br><span class="err">${esc(c.error?.code)}: ${esc(c.error?.message)}</span>`}</div>
    </div>`).join("") || `<div class="tc">no ${kind} calls</div>`;
}

function guardTone(guard) {
  if (!guard || !guard.controls_triggered?.length) return "good";
  return guard.allowed === false ? "bad" : "warn";
}

function setAnswer(el, data) {
  const refused = data.refused;
  const sanitized = data.output_guard?.action === "sanitize";
  el.className = `answer${refused ? " refused" : sanitized ? " blocked-out" : ""}`;
  el.dataset.state = refused ? "refused" : sanitized ? "sanitized" : "answered";
  el.textContent = data.answer || "(no answer)";
}

function busy(btn, on) { btn.disabled = on; btn.textContent = on ? "Working…" : btn.dataset.label; }

/* ---------------- RAG ---------------- */
$("ragSubmit").dataset.label = "Ask";
$("ragSubmit").addEventListener("click", async () => {
  const btn = $("ragSubmit"), q = $("ragInput").value.trim();
  if (!q) return;
  busy(btn, true);
  const { body } = await api("/api/rag/query", {
    method: "POST",
    body: JSON.stringify({
      query: q,
      top_k: Number($("ragTopK").value) || 4,
      guardrails: $("ragGuard").checked,
    }),
  });
  busy(btn, false);
  setAnswer($("ragAnswer"), body);
  const g = body.grounding || {};
  $("ragMeta").innerHTML = [
    metric("latency", `${body.latency_ms}ms`),
    metric("retrieved", (body.contexts || []).length, (body.contexts || []).length ? "good" : "bad"),
    metric("grounding", `${g.verdict ?? "n/a"} ${g.score ?? ""}`,
      g.verdict === "grounded" ? "good" : g.verdict === "ungrounded" ? "bad" : "warn"),
    metric("citations", (body.citations || []).join(",") || "none", (body.citations || []).length ? "good" : "bad"),
    metric("guard-in", body.input_guard?.controls_triggered?.join(",") || "clean", guardTone(body.input_guard)),
    metric("guard-out", body.output_guard?.action || "n/a", guardTone(body.output_guard)),
  ].join("");
  $("ragContexts").innerHTML = (body.contexts || []).map((c) => `
    <div class="ctx" data-doc="${esc(c.doc_id)}">
      <div class="ctx-head"><span class="ctx-doc">${esc(c.doc_id)} · ${esc(c.section)}</span>
        <span>score ${c.score} · rank ${c.rank} · ${esc(c.authority)}</span></div>
      <div class="ctx-body">${esc(c.text)}</div></div>`).join("") || '<div class="ctx">no context retrieved</div>';
  renderTrace($("ragTrace"), body.trace);
});

/* ---------------- Single agent ---------------- */
$("agentSubmit").dataset.label = "Run agent";
$("agentSubmit").addEventListener("click", async () => {
  const btn = $("agentSubmit"), q = $("agentInput").value.trim();
  if (!q) return;
  busy(btn, true);
  const { body } = await api("/api/agent/query", {
    method: "POST",
    body: JSON.stringify({ query: q, guardrails: $("agentGuard").checked }),
  });
  busy(btn, false);
  setAnswer($("agentAnswer"), body);
  $("agentMeta").innerHTML = [
    metric("latency", `${body.latency_ms}ms`),
    metric("steps", `${body.steps_used}/${body.max_steps}`,
      body.stopped_reason === "step_budget_exhausted" ? "bad" : "good"),
    metric("stop", body.stopped_reason, body.stopped_reason === "completed" ? "good" : "warn"),
    metric("tools", (body.tools_used || []).join(",") || "none"),
    metric("guard-in", body.input_guard?.controls_triggered?.join(",") || "clean", guardTone(body.input_guard)),
    metric("guard-out", body.output_guard?.action || "n/a", guardTone(body.output_guard)),
  ].join("");
  renderToolCalls($("agentTools"), body.tool_calls);
  renderTrace($("agentTrace"), body.trace);
});

/* ---------------- Multi-agent ---------------- */
$("multiSubmit").dataset.label = "Run team";
$("multiSubmit").addEventListener("click", async () => {
  const btn = $("multiSubmit"), q = $("multiInput").value.trim();
  if (!q) return;
  busy(btn, true);
  const { body } = await api("/api/multi/query", {
    method: "POST",
    body: JSON.stringify({ query: q, guardrails: $("multiGuard").checked }),
  });
  busy(btn, false);
  setAnswer($("multiAnswer"), body);
  $("multiMeta").innerHTML = [
    metric("latency", `${body.latency_ms}ms`),
    metric("agents", (body.agents_used || []).length, "good"),
    metric("subtasks", (body.subtasks || []).length),
    metric("transport", body.transport),
    metric("mcp calls", (body.mcp_calls || []).length),
    metric("guard-out", body.output_guard?.action || "n/a", guardTone(body.output_guard)),
  ].join("");
  $("multiPlan").innerHTML = (body.subtasks || []).map((t) => `
    <div class="task" data-specialist="${esc(t.specialist)}" data-status="${esc(t.status)}">
      <div class="task-head"><span class="ctx-doc">${esc(t.task_id)} · ${esc(t.specialist)}</span>
        <span>${esc(t.status)} · ${t.duration_ms}ms</span></div>
      <div class="ctx-body"><em>${esc(t.description)}</em><br>${esc((t.findings || t.error || "").slice(0, 400))}</div>
    </div>`).join("") || '<div class="task">no subtasks</div>';
  renderToolCalls($("multiCalls"), body.mcp_calls, "MCP");
});

/* ---------------- Tool console ---------------- */
let TOOLS = [];
async function loadTools() {
  const { body } = await api("/api/tools");
  TOOLS = body.tools || [];
  $("toolSelect").innerHTML = TOOLS.map((t) => `<option value="${esc(t.name)}">${esc(t.name)}</option>`).join("");
  showSchema();
}
function showSchema() {
  const t = TOOLS.find((x) => x.name === $("toolSelect").value);
  if (!t) return;
  const props = Object.entries(t.parameters?.properties || {})
    .map(([k, v]) => `${k}: ${v.type}${(t.parameters.required || []).includes(k) ? " (required)" : ""}`).join("\n");
  $("toolSchema").textContent = `${t.description}\nrisk: ${t.risk}\n\n${props}`;
}
$("toolSelect").addEventListener("change", showSchema);
$("toolSubmit").dataset.label = "Execute";
$("toolSubmit").addEventListener("click", async () => {
  const btn = $("toolSubmit");
  let args;
  try { args = JSON.parse($("toolArgs").value || "{}"); }
  catch (e) { $("toolResult").textContent = `Invalid JSON: ${e.message}`; $("toolResult").dataset.state = "invalid"; return; }
  busy(btn, true);
  const { body, status } = await api(`/api/tools/${$("toolSelect").value}`, {
    method: "POST", body: JSON.stringify({ arguments: args }),
  });
  busy(btn, false);
  $("toolResult").dataset.state = body.ok ? "ok" : "error";
  $("toolResult").dataset.status = status;
  $("toolResult").textContent = JSON.stringify(body, null, 2);
});

/* ---------------- Market data ---------------- */
$("mktSubmit").dataset.label = "Fetch";
$("mktSubmit").addEventListener("click", async () => {
  const btn = $("mktSubmit");
  busy(btn, true);
  const { body } = await api(`/api/market/${encodeURIComponent($("mktSymbol").value)}?kind=${$("mktKind").value}`);
  busy(btn, false);
  const tone = body.source === "live" ? "good" : body.source === "snapshot" ? "warn" : "bad";
  $("mktProvenance").dataset.source = body.source || "error";
  $("mktProvenance").innerHTML = [
    metric("source", body.source || "error", tone),
    metric("provider", body.provider || "n/a"),
    metric("as_of", body.as_of || "n/a"),
    metric("stale", String(body.stale), body.stale ? "warn" : "good"),
    ...(body.warnings || []).map((w) => metric("warning", w.slice(0, 70), "warn")),
  ].join("");
  const rows = body.data?.strikes;
  if (rows?.length) {
    const spot = body.data.underlying_value;
    const atm = rows.reduce((a, b) => Math.abs(b.strike - spot) < Math.abs(a.strike - spot) ? b : a);
    $("mktTable").innerHTML = `<table><thead><tr>
      <th>Call OI</th><th>Call IV</th><th>Call LTP</th><th>Strike</th><th>Put LTP</th><th>Put IV</th><th>Put OI</th>
      </tr></thead><tbody>${rows.map((r) => `<tr class="${r.strike === atm.strike ? "atm" : ""}">
        <td>${r.call_oi ?? "-"}</td><td>${r.call_iv ?? "-"}</td><td>${r.call_ltp ?? "-"}</td>
        <td>${r.strike}</td>
        <td>${r.put_ltp ?? "-"}</td><td>${r.put_iv ?? "-"}</td><td>${r.put_oi ?? "-"}</td></tr>`).join("")}
      </tbody></table>`;
  } else { $("mktTable").innerHTML = ""; }
  $("mktRaw").textContent = JSON.stringify(body, null, 2).slice(0, 6000);
});

/* ---------------- Settings modal ---------------- */
let PROVIDERS = [];

function renderProviderNote() {
  const p = PROVIDERS.find((x) => x.key === $("setProvider").value);
  if (!p) return;
  $("modelList").innerHTML = (p.models || []).map((m) => `<option value="${esc(m)}">`).join("");
  $("setModel").placeholder = p.default_model ? `default: ${p.default_model}` : "provider default";
  $("setKeyRow").hidden = !p.needs_key;
  const bits = [p.free_tier];
  if (p.notes) bits.push(p.notes);
  if (p.needs_key && p.console_url) bits.push(`Get a key: ${p.console_url}`);
  $("setProviderNote").textContent = bits.filter(Boolean).join("\n\n");
  $("setProviderNote").dataset.free = String(p.is_free);
  $("setProviderNote").dataset.localOnly = String(p.local_only);
}

async function loadProviders() {
  const { body } = await api("/api/providers");
  PROVIDERS = body.providers || [];
  $("setProvider").innerHTML = PROVIDERS.map((p) =>
    `<option value="${esc(p.key)}">${esc(p.label)}${p.is_free ? " — free" : " — paid"}</option>`).join("");
  $("setProvider").value = BACKEND.provider || body.offline_default || "stub";
  $("setModel").value = BACKEND.model || "";
  $("setKey").value = BACKEND.key || "";
  renderProviderNote();
}

function openSettings() { $("settingsModal").hidden = false; loadProviders(); }
function closeSettings() { $("settingsModal").hidden = true; }

$("openSettings").addEventListener("click", openSettings);
$("setClose").addEventListener("click", closeSettings);
$("settingsModal").addEventListener("click", (e) => { if (e.target.id === "settingsModal") closeSettings(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeSettings(); });
$("setProvider").addEventListener("change", () => { $("setKey").value = ""; renderProviderNote(); });

$("setVerify").dataset.label = "Verify key";
$("setVerify").addEventListener("click", async () => {
  const btn = $("setVerify");
  BACKEND = {
    provider: $("setProvider").value,
    model: $("setModel").value.trim(),
    key: $("setKey").value.trim(),
  };
  saveBackend();
  busy(btn, true);
  const { body, status } = await api("/api/llm/verify", {
    method: "POST", body: JSON.stringify({ prompt: "Reply with the single word: ready" }),
  });
  busy(btn, false);
  const ok = body.ok === true;
  $("setResult").dataset.state = ok ? "ok" : "error";
  $("setResult").innerHTML = ok
    ? [metric("backend", `${body.provider}/${body.model}`, "good"),
       metric("latency", `${body.latency_ms}ms`),
       metric("reply", (body.reply || "").slice(0, 40) || "(empty)", "good")].join("")
    : metric("failed", body.error || body.detail || `HTTP ${status}`, "bad");
  loadStatus();
});

$("setClear").addEventListener("click", () => {
  BACKEND = { provider: "stub", model: "", key: "" };
  saveBackend();
  $("setKey").value = "";
  $("setProvider").value = "stub";
  renderProviderNote();
  $("setResult").dataset.state = "cleared";
  $("setResult").innerHTML = metric("key", "forgotten — back to the offline stub", "warn");
  loadStatus();
});

/* ---------------- Test runner ---------------- */
async function loadSuites() {
  const { body } = await api("/api/tests/suites");
  $("runCategory").innerHTML = '<option value="">all</option>' +
    (body.categories || []).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
}

$("runSubmit").dataset.label = "Run";
$("runSubmit").addEventListener("click", async () => {
  const btn = $("runSubmit");
  busy(btn, true);
  $("runResults").innerHTML = '<div class="run">Running…</div>';
  const { body, status } = await api("/api/tests/run", {
    method: "POST",
    body: JSON.stringify({
      suite: $("runSuite").value || null,
      category: $("runCategory").value || null,
      limit: Number($("runLimit").value) || 20,
      use_my_model: $("runMine").checked,
    }),
  });
  busy(btn, false);
  if (!body.summary) {
    $("runResults").innerHTML = `<div class="run fail"><span class="err">${esc(body.detail || body.message || `HTTP ${status}`)}</span></div>`;
    $("runSummary").innerHTML = "";
    return;
  }
  const s = body.summary;
  $("runSummary").dataset.rate = String(s.pass_rate);
  $("runSummary").innerHTML = [
    metric("passed", `${s.passed}/${s.total}`, s.failed ? "bad" : "good"),
    metric("rate", `${s.pass_rate}%`, s.failed ? "warn" : "good"),
    metric("backend", body.backend?.provider || "stub"),
    metric("time", `${s.total_duration_ms}ms`),
    ...(body.truncated ? [metric("note", "capped — run locally for the full suite", "warn")] : []),
  ].join("");
  $("runResults").innerHTML = (body.results || []).map((r) => {
    const why = (r.checks || []).filter((c) => !c.passed)
      .map((c) => `${esc(c.type)}: ${esc(c.message)}`).join("<br>");
    return `<div class="run ${r.passed ? "" : "fail"}" data-case="${esc(r.id)}" data-passed="${r.passed}">
      <div class="run-head"><span>${esc(r.id)} · ${esc(r.category)} · ${esc(r.severity)}</span>
        <span>${r.passed ? "PASS" : "FAIL"} · ${r.duration_ms}ms</span></div>
      <div class="run-title">${esc(r.title)}</div>
      ${why ? `<div class="run-why">${why}</div>` : ""}
      ${r.passed ? "" : `<div class="file"><button class="chip file-btn" data-case="${esc(r.id)}">File this as a finding →</button></div>`}
    </div>`;
  }).join("") || '<div class="run">no cases matched</div>';

  // Pre-fill the findings form straight from a failure.
  $("runResults").querySelectorAll(".file-btn").forEach((b) => {
    b.addEventListener("click", () => {
      const r = (body.results || []).find((x) => x.id === b.dataset.case);
      if (!r) return;
      $("isTitle").value = `${r.id} — ${r.title}`.slice(0, 200);
      $("isSeverity").value = r.severity || "medium";
      $("isSteps").value = JSON.stringify(r.input || {}, null, 2);
      $("isExpected").value = (r.checks || []).filter((c) => !c.passed)
        .map((c) => c.type).join(", ");
      $("isActual").value = (r.checks || []).filter((c) => !c.passed)
        .map((c) => `${c.type}: ${c.message}`).join("\n");
      $("isImpact").value = "";
      document.querySelector('[data-testid="tab-issues"]').click();
      $("isImpact").focus();
    });
  });
});

/* ---------------- Findings ---------------- */
const AREAS = ["rag_retrieval","rag_grounding","citations","tool_selection","tool_contract",
  "agent_control_flow","mcp_routing","multi_agent","guardrail_input","guardrail_output",
  "market_data","pricing_math","ui","performance","other"];
$("isArea").innerHTML = AREAS.map((a) => `<option${a === "other" ? " selected" : ""}>${a}</option>`).join("");

$("isSubmit").dataset.label = "File finding";
$("isSubmit").addEventListener("click", async () => {
  const btn = $("isSubmit");
  const title = $("isTitle").value.trim();
  if (title.length < 3) { $("isStatus").textContent = "A finding needs a title."; return; }
  busy(btn, true);
  const { body, status } = await api("/api/issues", {
    method: "POST",
    body: JSON.stringify({
      title, area: $("isArea").value, severity: $("isSeverity").value,
      steps: $("isSteps").value, expected: $("isExpected").value,
      actual: $("isActual").value, impact: $("isImpact").value,
      reporter: $("isReporter").value, case_id: "",
    }),
  });
  busy(btn, false);
  if (body.issue) {
    $("isStatus").textContent = `Filed ${body.issue.id}.`;
    $("isStatus").dataset.state = "filed";
    ["isTitle","isSteps","isExpected","isActual","isImpact"].forEach((id) => { $(id).value = ""; });
    loadIssues();
  } else {
    $("isStatus").textContent = body.detail || body.message || `HTTP ${status}`;
    $("isStatus").dataset.state = "error";
  }
});

async function loadIssues() {
  const { body } = await api("/api/issues?limit=100");
  const s = body.stats || {};
  $("isStats").innerHTML = [
    metric("total", s.total ?? 0),
    metric("open", s.open ?? 0, s.open ? "warn" : "good"),
    metric("critical open", s.critical_open ?? 0, s.critical_open ? "bad" : "good"),
  ].join("");
  $("isList").innerHTML = (body.issues || []).map((i) => `
    <div class="issue" data-id="${esc(i.id)}" data-severity="${esc(i.severity)}">
      <div class="issue-head">
        <span class="sev-${esc(i.severity)}">${esc(i.id)} · ${esc(i.severity)}</span>
        <span>${esc(i.area)} · ${esc(i.status)} · ${esc(i.reporter || "anon")}</span>
      </div>
      <div class="run-title">${esc(i.title)}</div>
      ${i.impact ? `<div class="ctx-body" style="margin-top:6px">${esc(i.impact)}</div>` : ""}
    </div>`).join("") || '<div class="issue">No findings filed yet.</div>';
}

function refreshMode() {
  $("modeState").innerHTML = [
    metric("guardrails", "per request", "good"),
    metric("scope", "your session only", "good"),
  ].join("");
}

async function loadMcp() {
  const { body } = await api("/api/mcp/servers");
  $("mcpServers").innerHTML = (body.servers || []).map((s) => `
    <div class="tc" data-server="${esc(s.key)}">
      <div class="tc-head"><span class="ctx-doc">${esc(s.key)}</span>
        <span>${esc(s.serverInfo?.name || "")} v${esc(s.serverInfo?.version || "")} · ${esc(body.transport)}</span></div>
      <div class="ctx-body">tools: ${esc((s.tools || []).join(", "))}</div></div>`).join("");
}

async function loadKb() {
  const { body } = await api("/api/kb/stats");
  $("kbStats").innerHTML = Object.entries(body)
    .map(([k, v]) => metric(k, Array.isArray(v) ? v.join(",") : v)).join("");
}

async function loadStatus() {
  const { body } = await api("/api/health");
  const keyed = BACKEND.key ? " · your key" : "";
  $("pillProvider").textContent = `llm: ${BACKEND.provider}${BACKEND.model ? "/" + BACKEND.model : ""}${keyed}`;
  $("pillProvider").className = `pill ${BACKEND.provider === "stub" ? "" : "good"}`;
  $("pillProvider").dataset.provider = BACKEND.provider;
  $("pillMarket").textContent = `market: ${body.market_mode} · ${body.mode}`;
  $("pillKb").textContent = `kb: ${body.knowledge_chunks} chunks · ${body.tools} tools · ${body.issues_open} open`;
  const anyOff = ["ragGuard", "agentGuard", "multiGuard"].some((id) => $(id) && !$(id).checked);
  $("pillGuard").textContent = `guardrails: ${anyOff ? "OFF on a panel" : "on"}`;
  $("pillGuard").className = `pill ${anyOff ? "bad" : "good"}`;
  document.body.dataset.vulnerable = String(anyOff);
}
["ragGuard", "agentGuard", "multiGuard"].forEach((id) => {
  const el = $(id);
  if (el) el.addEventListener("change", loadStatus);
});

loadStatus(); loadTools(); loadMcp(); loadKb(); refreshMode(); loadSuites(); loadIssues(); loadProviders();
