/* Test Lab — sign in, run the published IEEE suite, mark results, raise defects.

   Two rules this file exists to enforce on the client side:

   1. The model key is never sent anywhere but this app's own API, as a header,
      exactly as it was before sign-in existed. Signing in says whose results
      these are; it does not hand this server anyone's credentials.
   2. Nothing here assumes you are signed in. The catalogue and the published
      defect board are readable signed out, because a trainee should be able to
      see what the suite contains before deciding to log in. */

const LAB = {
  user: null,
  config: null,
  suite: "rag",
  cases: [],
  selected: new Set(),
  defectFor: null,
};

const el = (id) => document.getElementById(id);

/* ---------------- sign in ---------------- */
async function loadAuth() {
  const { body } = await api("/api/auth/me");
  LAB.user = body.user;
  LAB.config = body.config || {};
  renderAuth();
  if (LAB.user) { loadSummary(); loadMyDefects(); loadAccount(); }
  loadCatalogue();
  loadPublicDefects();
}

function renderAuth() {
  const signedIn = !!LAB.user;
  el("openSignin").hidden = signedIn;
  el("openAccount").hidden = !signedIn;
  if (signedIn) el("openAccount").textContent = LAB.user.name || LAB.user.email;

  const box = el("signinBox");
  if (box) {
    box.dataset.state = signedIn ? "signed-in" : "signed-out";
    el("signedIn").hidden = !signedIn;
    el("signedOut").hidden = signedIn;
    if (signedIn) {
      el("whoName").textContent = LAB.user.name || LAB.user.email;
      el("whoMail").textContent = LAB.user.email;
    }
  }
  el("localSignin").hidden = !LAB.config.local_enabled;
  const gh = el("googleHint");
  if (LAB.config.google_enabled) { gh.hidden = true; mountGoogle(); }
  else {
    gh.hidden = false;
    gh.textContent = "Google sign-in is not configured on this instance, so use an email and "
      + "passcode below.";
  }
}

let googleMounted = false;
function mountGoogle() {
  if (googleMounted || !window.google?.accounts?.id || !LAB.config.google_client_id) return;
  googleMounted = true;
  window.google.accounts.id.initialize({
    client_id: LAB.config.google_client_id,
    callback: async (response) => {
      const { status, body } = await api("/api/auth/google", {
        method: "POST", body: JSON.stringify({ credential: response.credential }),
      });
      if (status === 200) signedInAs(body.user);
      else el("acError").textContent = errorText(body, status, "Sign-in failed.");
    },
  });
  window.google.accounts.id.renderButton(el("googleBtn"), { theme: "outline", size: "large" });
}
let gsiTries = 0;
const gsiTimer = setInterval(() => {
  if (googleMounted || ++gsiTries > 40) return clearInterval(gsiTimer);
  if (!LAB.user && LAB.config?.google_enabled) mountGoogle();
}, 250);

function signedInAs(user) {
  LAB.user = user;
  el("signinModal").hidden = true;
  el("acPasscode").value = "";
  renderAuth();
  loadSummary(); loadMyDefects(); loadCatalogue(); loadAccount();
}

/* The modal is reachable from the header, from the Test Lab and from My Account,
   because "where do I sign in" should never need a hunt. */
function openSignin() {
  // Always open on "I have an account". The modal used to remember whichever
  // mode you last used, so signing out and back in tried to register the same
  // address again and told you it already existed — technically true, useless.
  setMode(false);
  el("acPasscode").value = "";
  el("acError").textContent = "";
  el("signinModal").hidden = false;
  el("acEmail").focus();
}
["openSignin", "labSignin", "accountSignin"].forEach((id) =>
  el(id)?.addEventListener("click", openSignin));
el("acCancel")?.addEventListener("click", () => { el("signinModal").hidden = true; });
el("signinModal")?.addEventListener("click", (e) => {
  if (e.target.id === "signinModal") el("signinModal").hidden = true;
});
el("openAccount")?.addEventListener("click", () => {
  document.querySelector('[data-testid="tab-account"]').click();
});

let signupMode = false;
function setMode(signup) {
  signupMode = signup;
  el("modeSignup").classList.toggle("active", signup);
  el("modeSignin").classList.toggle("active", !signup);
  el("acNameRow").hidden = !signup;
  el("acGo").textContent = signup ? "Create account" : "Sign in";
  el("acPasscode").setAttribute("autocomplete", signup ? "new-password" : "current-password");
  el("acHint").textContent = signup
    ? `At least ${LAB.config.min_passcode || 8} characters. It is hashed before storage — this `
      + "instance never holds your passcode, and it must not be your email password."
    : "The passcode you chose when you created this account on this instance.";
  el("acError").textContent = "";
}
el("modeSignup")?.addEventListener("click", () => setMode(true));
el("modeSignin")?.addEventListener("click", () => setMode(false));

async function submitAccount() {
  const email = el("acEmail").value.trim();
  const passcode = el("acPasscode").value;
  if (!email || !passcode) { el("acError").textContent = "Email and passcode are both needed."; return; }
  const path = signupMode ? "/api/auth/signup" : "/api/auth/signin";
  const payload = signupMode
    ? { email, passcode, name: el("acName").value.trim() }
    : { email, passcode };
  busy(el("acGo"), true);
  const { status, body } = await api(path, { method: "POST", body: JSON.stringify(payload) });
  busy(el("acGo"), false);
  if (status === 200 || status === 201) return signedInAs(body.user);
  el("acError").textContent = errorText(body, status, "Sign-in failed.");
}
el("acGo")?.addEventListener("click", submitAccount);
["acEmail", "acPasscode", "acName"].forEach((id) =>
  el(id)?.addEventListener("keydown", (e) => { if (e.key === "Enter") submitAccount(); }));

el("localGo")?.addEventListener("click", async () => {
  const { status, body } = await api("/api/auth/local", {
    method: "POST", body: JSON.stringify({ name: el("localName").value.trim() || "trainee" }),
  });
  if (status === 200) signedInAs(body.user);
  else el("acError").textContent = errorText(body, status, "Sign-in failed.");
});

el("signOut")?.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  LAB.user = null; renderAuth(); loadCatalogue();
  el("labDash").innerHTML = ""; el("myDefects").innerHTML = "";
  el("accountBody").dataset.state = "signed-out";
  loadAccount();
});

/* ---------------- my account ---------------- */
/* Refresh on open. Rendering this page once at sign-in means a trainee runs
   twenty cases, clicks My Account and reads "0 executed" — stale numbers on a
   reporting page are worse than no numbers. */
document.querySelector('[data-testid="tab-account"]')?.addEventListener("click", () => loadAccount());
document.querySelector('[data-testid="tab-board"]')?.addEventListener("click", () => {
  loadMyDefects(); loadPublicDefects();
});

async function loadAccount() {
  const box = el("accountBody");
  if (!box) return;
  if (!LAB.user) {
    box.dataset.state = "signed-out";
    box.innerHTML = '<p class="hint">Sign in to see your account, your execution history and '
      + 'your reports.</p><button class="primary" id="accountSignin2" '
      + 'data-testid="account-signin">Sign in</button>';
    el("accountSignin2")?.addEventListener("click", openSignin);
    return;
  }
  const { body } = await api("/api/lab/account");
  const s = body.summary || {};
  const t = s.totals || {};
  box.dataset.state = "signed-in";
  box.dataset.executed = String(s.executed || 0);
  box.innerHTML = `
    <div class="acct-head">
      <div>
        <h3>${esc(body.user.name || body.user.email)}</h3>
        <p class="hint mono">${esc(body.user.email)} · signed in via ${esc(body.user.provider)}</p>
      </div>
      <div class="acct-actions">
        <a class="ghost" href="/api/lab/report" data-testid="dl-md">Report (markdown)</a>
        <a class="ghost" href="/api/lab/report.csv" data-testid="dl-csv">Results (CSV)</a>
        <button class="ghost" id="acctSignOut" data-testid="acct-signout">Sign out</button>
      </div>
    </div>
    <div class="dash">
      <div class="dashcard"><h4>Executed</h4>
        <div class="dashbig" data-testid="acct-executed">${s.executed || 0}</div>
        <div class="dashlegend"><span class="ok">${t.Pass || 0} pass</span>
          <span class="bad">${t.Fail || 0} fail</span>
          <span class="warn">${t["Fail (expected)"] || 0} gap</span>
          <span class="mute">${t.Blocked || 0} blocked</span></div></div>
      <div class="dashcard"><h4>Defects</h4>
        <div class="dashbig" data-testid="acct-defects">${s.defects?.total || 0}</div>
        <div class="dashlegend"><span>${s.defects?.published || 0} published</span></div></div>
      <div class="dashcard"><h4>Coverage</h4>
        <div class="dashbig">${Math.round(((s.executed || 0) / 377) * 100)}%</div>
        <div class="dashlegend"><span>of the 377 published cases</span></div></div>
      <div class="dashcard"><h4>Last run</h4>
        <div class="dashbig sm">${s.last_run_at
          ? new Date(s.last_run_at * 1000).toLocaleString() : "—"}</div></div>
    </div>

    <h3>Execution history</h3>
    <div class="scroll"><table class="acct-table" data-testid="acct-history">
      <thead><tr><th>Case</th><th>Suite</th><th>Area</th><th>Harness</th><th>My verdict</th>
        <th>When</th></tr></thead>
      <tbody>${(body.history || []).map((r) => `<tr>
        <td class="mono">${esc(r.case_id)}</td><td>${esc(r.suite)}</td><td>${esc(r.area)}</td>
        <td><span class="metric ${{ Pass: "ok", Fail: "bad", "Fail (expected)": "warn" }[r.status] || ""}">${esc(r.status)}</span></td>
        <td>${r.verdict ? esc(r.verdict) : "—"}</td>
        <td class="mono">${new Date(r.created_at * 1000).toLocaleString()}</td></tr>`).join("")
        || '<tr><td colspan="6" class="hint">Nothing run yet — open the Test Lab.</td></tr>'}
      </tbody></table></div>

    <h3>My defects</h3>
    <div class="scroll"><table class="acct-table" data-testid="acct-defects-table">
      <thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Case</th><th>Published</th></tr></thead>
      <tbody>${(body.defects || []).map((d) => `<tr>
        <td class="mono">${esc(d.id)}</td><td>${esc(d.title)}</td>
        <td>${esc(d.severity)}</td><td class="mono">${esc(d.case_id || "—")}</td>
        <td>${d.published ? "yes" : "no"}</td></tr>`).join("")
        || '<tr><td colspan="5" class="hint">No defects raised yet.</td></tr>'}
      </tbody></table></div>

    <p class="hint">This instance stores results in a SQLite file. On a free hosting tier that
      disk is wiped by a redeploy — download your report before you finish.</p>`;
  el("acctSignOut")?.addEventListener("click", async () => {
    await api("/api/auth/logout", { method: "POST" });
    LAB.user = null; renderAuth(); loadCatalogue(); loadAccount();
    el("labDash").innerHTML = "";
  });
}

/* ---------------- dashboard ---------------- */
async function loadSummary() {
  if (!LAB.user) return;
  const { body } = await api("/api/lab/summary");
  renderDash(body.summary);
}

const SUITE_LABEL = { rag: "RAG Assistant", agent: "Single Agent", multi: "Multi-Agent" };

function renderDash(summary) {
  const box = el("labDash");
  if (!box) return;
  if (!summary) { box.innerHTML = ""; return; }
  box.dataset.executed = String(summary.executed || 0);
  const cards = ["rag", "agent", "multi"].map((suite) => {
    const s = summary.by_suite[suite] || { total: 0, Pass: 0, Fail: 0, "Fail (expected)": 0, Blocked: 0 };
    const run = s.total || 0;
    const rate = run ? Math.round((s.Pass / run) * 100) : 0;
    return `<div class="dashcard" data-suite="${suite}" data-testid="dash-${suite}">
      <h4>${SUITE_LABEL[suite]}</h4>
      <div class="dashbig"><span data-testid="dash-${suite}-run">${run}</span> <small>executed</small></div>
      <div class="bar" role="img" aria-label="${rate}% passing">
        <span class="seg ok"   style="width:${run ? (s.Pass / run) * 100 : 0}%"></span>
        <span class="seg bad"  style="width:${run ? (s.Fail / run) * 100 : 0}%"></span>
        <span class="seg warn" style="width:${run ? (s["Fail (expected)"] / run) * 100 : 0}%"></span>
        <span class="seg mute" style="width:${run ? (s.Blocked / run) * 100 : 0}%"></span>
      </div>
      <div class="dashlegend">
        <span class="ok">${s.Pass} pass</span><span class="bad">${s.Fail} fail</span>
        <span class="warn">${s["Fail (expected)"]} gap</span><span class="mute">${s.Blocked} blocked</span>
      </div>
    </div>`;
  }).join("");
  const d = summary.defects || { total: 0, published: 0 };
  box.innerHTML = cards + `<div class="dashcard" data-testid="dash-defects">
      <h4>Defects</h4>
      <div class="dashbig"><span data-testid="defect-count">${d.total}</span> <small>raised</small></div>
      <div class="dashlegend"><span>${d.published} published</span>
        <span class="bad">${d.by_severity?.critical || 0} critical</span>
        <span class="warn">${d.by_severity?.high || 0} high</span></div>
      <button class="ghost" id="newDefect" data-testid="new-defect">Raise a defect</button>
    </div>`;
  el("newDefect")?.addEventListener("click", () => openDefect(null));
}

/* ---------------- catalogue ---------------- */
async function loadCatalogue() {
  const box = el("caseList");
  if (!box) return;
  box.dataset.state = "loading";
  const { body } = await api(`/api/lab/catalogue?suite=${LAB.suite}`);
  LAB.cases = body.cases || [];
  const areas = [...new Set(LAB.cases.map((c) => c.area))].sort();
  const sel = el("labArea");
  const current = sel.value;
  sel.innerHTML = '<option value="">all areas</option>' +
    areas.map((a) => `<option value="${a}">${a}</option>`).join("");
  if (areas.includes(current)) sel.value = current;
  renderCases();
}

function visibleCases() {
  const area = el("labArea").value;
  const filter = el("labFilter").value;
  const needle = el("labSearch").value.trim().toLowerCase();
  return LAB.cases.filter((c) => {
    if (area && c.area !== area) return false;
    if (filter === "notrun" && c.result) return false;
    if (filter && filter !== "notrun" && c.result?.status !== filter) return false;
    if (needle && !(`${c.id} ${c.objective} ${c.input} ${c.category}`.toLowerCase().includes(needle)))
      return false;
    return true;
  });
}

function renderCases() {
  const box = el("caseList");
  const rows = visibleCases();
  box.dataset.state = rows.length ? "loaded" : "empty";
  box.dataset.count = String(rows.length);
  box.innerHTML = rows.map((c) => {
    const r = c.result;
    const status = r?.status || "not run";
    const cls = { Pass: "ok", Fail: "bad", "Fail (expected)": "warn", Blocked: "mute" }[status] || "";
    return `<article class="case" data-case="${esc(c.id)}" data-status="${esc(status)}"
             data-capability="${esc(c.capability)}" data-testid="case-${esc(c.id)}">
      <div class="case-head">
        <label class="pick"><input type="checkbox" data-pick="${esc(c.id)}"
          ${LAB.selected.has(c.id) ? "checked" : ""} aria-label="select ${esc(c.id)}"></label>
        <span class="case-id">${esc(c.id)}</span>
        <span class="chip-sm">${esc(c.area)}</span>
        <span class="chip-sm cap-${esc(c.capability)}">${esc(c.capability)}</span>
        <span class="metric ${cls}" data-testid="status-${esc(c.id)}">${esc(status)}</span>
        ${r?.verdict ? `<span class="chip-sm verdict">marked ${esc(r.verdict)}</span>` : ""}
      </div>
      <p class="case-obj">${esc(c.objective)}</p>
      <details class="case-detail">
        <summary>steps, expected result and what this sends</summary>
        <div class="case-grid">
          <div><b>Test data</b><p>${esc(c.data)}</p></div>
          <div><b>Steps</b><pre>${esc(c.steps)}</pre></div>
          <div><b>Expected</b><p>${esc(c.expected)}</p></div>
          <div><b>Sent to this system</b><p class="mono">${esc(c.input) || "—"}</p></div>
          ${c.note ? `<div><b>Binding note</b><p>${esc(c.note)}</p></div>` : ""}
        </div>
      </details>
      ${r ? `<div class="case-result" data-testid="result-${esc(c.id)}">
        <div class="case-actual">${esc(r.actual)}</div>
        ${r.remark ? `<div class="case-remark">${esc(r.remark)}</div>` : ""}
        <div class="case-actions">
          <span class="hint">${Math.round(r.duration_ms)}ms · your call:</span>
          ${["pass", "fail", "blocked"].map((v) => `<button class="ghost verdict-btn"
             data-verdict="${v}" data-for="${esc(c.id)}"
             data-testid="verdict-${v}-${esc(c.id)}">${v}</button>`).join("")}
          <button class="ghost" data-defect="${esc(c.id)}"
            data-testid="defect-${esc(c.id)}">Raise defect</button>
        </div></div>` : ""}
      <div class="case-run">
        <button class="primary sm" data-run="${esc(c.id)}" data-testid="run-${esc(c.id)}"
          ${c.runnable ? "" : "disabled title='Runs load — execute this one locally'"}>
          ${r ? "Run again" : "Run"}</button>
      </div>
    </article>`;
  }).join("") || '<p class="hint">No cases match those filters.</p>';
}

document.querySelectorAll(".suitetab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".suitetab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    LAB.suite = tab.dataset.suite;
    LAB.selected.clear();
    loadCatalogue();
  });
});
["labArea", "labFilter"].forEach((id) => el(id)?.addEventListener("change", renderCases));
el("labSearch")?.addEventListener("input", renderCases);

el("caseList")?.addEventListener("click", async (e) => {
  const t = e.target;
  if (t.dataset.run) return runCases([t.dataset.run], t);
  if (t.dataset.verdict) return markVerdict(t.dataset.for, t.dataset.verdict);
  if (t.dataset.defect) return openDefect(t.dataset.defect);
});
el("caseList")?.addEventListener("change", (e) => {
  const id = e.target.dataset?.pick;
  if (!id) return;
  e.target.checked ? LAB.selected.add(id) : LAB.selected.delete(id);
});

el("runSelected")?.addEventListener("click", (e) => {
  const ids = [...LAB.selected].slice(0, 40);
  if (!ids.length) return alert("Tick some cases first.");
  runCases(ids, e.target);
});

async function runCases(ids, button) {
  if (!LAB.user) {
    el("caseList").dataset.state = "needs-signin";
    return alert("Sign in first — results are stored against your account.");
  }
  if (button) busy(button, true);
  const { status, body } = await api("/api/lab/run", {
    method: "POST", body: JSON.stringify({ case_ids: ids }),
  });
  if (button) busy(button, false);
  if (status !== 200) return alert(errorText(body, status, "Run failed."));
  renderDash(body.summary);
  await loadCatalogue();
  loadAccount();
}

async function markVerdict(caseId, verdict) {
  const { status, body } = await api("/api/lab/verdict", {
    method: "POST", body: JSON.stringify({ case_id: caseId, verdict }),
  });
  if (status !== 200) return alert(errorText(body, status, "Could not record that verdict."));
  await loadCatalogue();
}

/* ---------------- defects ---------------- */
function openDefect(caseId) {
  LAB.defectFor = caseId;
  const c = caseId ? LAB.cases.find((x) => x.id === caseId) : null;
  el("defectCase").textContent = c ? `Against ${c.id} — ${c.category}` : "Not linked to a test case.";
  el("dTitle").value = c ? `${c.id}: ${(c.objective || "").slice(0, 120)}` : "";
  el("dSuite").value = c?.suite || LAB.suite;
  el("dSteps").value = c ? (c.steps || "") : "";
  el("dExpected").value = c ? (c.expected || "") : "";
  el("dActual").value = c?.result ? `${c.result.actual}\n\n${c.result.remark || ""}`.trim() : "";
  el("dSeverity").value = c?.capability === "absent" ? "medium" : "high";
  el("dStatus").textContent = "";
  el("dPublish").checked = false;
  el("defectModal").hidden = false;
}
el("dCancel")?.addEventListener("click", () => { el("defectModal").hidden = true; });
el("defectModal")?.addEventListener("click", (e) => {
  if (e.target.id === "defectModal") el("defectModal").hidden = true;
});

el("dSave")?.addEventListener("click", async () => {
  if (!LAB.user) return alert("Sign in to raise a defect.");
  const payload = {
    title: el("dTitle").value.trim(), severity: el("dSeverity").value,
    suite: el("dSuite").value, case_id: LAB.defectFor || null,
    steps: el("dSteps").value, expected: el("dExpected").value, actual: el("dActual").value,
  };
  if (payload.title.length < 3) { el("dStatus").textContent = "A defect needs a title."; return; }
  const { status, body } = await api("/api/lab/defects", {
    method: "POST", body: JSON.stringify(payload),
  });
  if (status !== 201) { el("dStatus").textContent = errorText(body, status, "Could not save."); return; }
  if (el("dPublish").checked) {
    await api(`/api/lab/defects/${body.defect.id}/publish?publish=true`, { method: "POST" });
  }
  el("defectModal").hidden = true;
  loadMyDefects(); loadPublicDefects(); loadSummary();
});

async function loadMyDefects() {
  const box = el("myDefects");
  if (!box || !LAB.user) { if (box) box.innerHTML = '<p class="hint">Sign in to see your defects.</p>'; return; }
  const { body } = await api("/api/lab/defects");
  const rows = body.defects || [];
  box.dataset.state = rows.length ? "loaded" : "empty";
  box.dataset.count = String(rows.length);
  box.innerHTML = rows.map((d) => `
    <article class="defect" data-defect="${esc(d.id)}" data-published="${d.published}"
             data-testid="defect-row-${esc(d.id)}">
      <div class="defect-head">
        <span class="case-id">${esc(d.id)}</span>
        <span class="chip-sm sev-${esc(d.severity)}">${esc(d.severity)}</span>
        <span class="chip-sm">${esc(d.suite)}</span>
        ${d.case_id ? `<span class="chip-sm">${esc(d.case_id)}</span>` : ""}
        <span class="chip-sm ${d.published ? "verdict" : ""}">${d.published ? "published" : "private"}</span>
      </div>
      <p class="defect-title">${esc(d.title)}</p>
      ${d.actual ? `<div class="case-actual">${esc(d.actual.slice(0, 300))}</div>` : ""}
      <div class="case-actions">
        <button class="ghost" data-publish="${esc(d.id)}" data-to="${d.published ? "false" : "true"}"
          data-testid="publish-${esc(d.id)}">${d.published ? "Withdraw" : "Publish"}</button>
        <button class="ghost" data-del="${esc(d.id)}" data-testid="delete-${esc(d.id)}">Delete</button>
      </div>
    </article>`).join("") || '<p class="hint">No defects raised yet.</p>';
}

el("myDefects")?.addEventListener("click", async (e) => {
  const t = e.target;
  if (t.dataset.publish) {
    await api(`/api/lab/defects/${t.dataset.publish}/publish?publish=${t.dataset.to}`,
      { method: "POST" });
    loadMyDefects(); loadPublicDefects(); loadSummary();
  }
  if (t.dataset.del) {
    await api(`/api/lab/defects/${t.dataset.del}`, { method: "DELETE" });
    loadMyDefects(); loadPublicDefects(); loadSummary();
  }
});

async function loadPublicDefects() {
  const box = el("publicDefects");
  if (!box) return;
  const { body } = await api("/api/public/defects");
  const rows = body.defects || [];
  box.dataset.count = String(rows.length);
  box.innerHTML = rows.map((d) => `
    <article class="defect" data-testid="public-${esc(d.id)}">
      <div class="defect-head">
        <span class="case-id">${esc(d.id)}</span>
        <span class="chip-sm sev-${esc(d.severity)}">${esc(d.severity)}</span>
        <span class="chip-sm">${esc(d.suite)}</span>
        <span class="chip-sm">${esc(d.reporter)}</span>
      </div>
      <p class="defect-title">${esc(d.title)}</p>
    </article>`).join("") || '<p class="hint">Nothing published yet.</p>';
}

setMode(false);
loadAuth();
