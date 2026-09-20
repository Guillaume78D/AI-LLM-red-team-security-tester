const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const LABELS = {
  prompt_injection: "Prompt Injection",
  instruction_conflict: "Instruction Conflict",
  system_prompt_extraction: "System Prompt Extraction",
  jailbreak: "Jailbreak Resistance",
  sensitive_leakage: "Sensitive Information Leakage",
};

let allResults = [];
let currentFilter = "ALL";

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.json();
}

function showError(msg) {
  const box = $("#error");
  box.textContent = msg;
  box.classList.remove("hidden");
}

function renderCards(s) {
  const cards = [
    ["Total Tests", s.total, ""],
    ["Passed", s.passed, "green"],
    ["Failed", s.failed, "red"],
    ["Critical", s.severity.CRITICAL, "crit"],
    ["High", s.severity.HIGH, "red"],
    ["Medium", s.severity.MEDIUM, "orange"],
    ["Low", s.severity.LOW, "blue"],
  ];
  $("#cards").innerHTML = cards.map(([label, value, cls]) =>
    `<div class="card ${cls}"><div class="label">${label}</div><div class="value">${value}</div></div>`
  ).join("");
}

function renderRisk(s) {
  const parts = [
    ["Passed", s.passed, "#22c55e"],
    ["Critical", s.severity.CRITICAL, "#b91c1c"],
    ["High", s.severity.HIGH, "#ef4444"],
    ["Medium", s.severity.MEDIUM, "#f59e0b"],
    ["Low", s.severity.LOW, "#3b82f6"],
    ["Errors", s.errors, "#6b7280"],
  ];
  const total = parts.reduce((sum, p) => sum + p[1], 0);
  let acc = 0;
  const stops = [];
  parts.forEach(([, n, color]) => {
    if (!n) return;
    const start = (acc / total) * 100;
    acc += n;
    stops.push(`${color} ${start}% ${(acc / total) * 100}%`);
  });
  if (stops.length) $("#donut").style.background = `conic-gradient(${stops.join(",")})`;
  $("#donut-total").textContent = s.total;

  const badge = $("#risk-badge");
  badge.textContent = s.risk_level;
  badge.className = `risk-badge risk-${s.risk_level}`;
  $("#risk-score").textContent = `Risk score: ${s.risk_score}%`;
  $("#legend").innerHTML = parts.filter((p) => p[1] > 0).map(([label, n, color]) =>
    `<li><span class="dot" style="background:${color}"></span>${label} (${n})</li>`
  ).join("");
}

function renderCategories(s) {
  $("#categories").innerHTML = Object.entries(s.categories).map(([key, c]) => {
    const pct = c.total ? (c.passed / c.total) * 100 : 0;
    return `<div class="cat">
      <div class="cat-head"><span>${esc(LABELS[key] || key)}</span><span>${c.passed}/${c.total} passed</span></div>
      <div class="bar"><span style="width:${pct}%"></span></div>
    </div>`;
  }).join("");
}

function renderTable() {
  const rows = allResults.filter((r) => currentFilter === "ALL" || r.status === currentFilter);
  $("#results-body").innerHTML = rows.map((r) => `
    <tr class="main">
      <td>${esc(r.test_id)}</td>
      <td>${esc(LABELS[r.category] || r.category)}</td>
      <td><span class="badge ${r.status}">${r.status}</span></td>
      <td class="${r.status === "FAIL" ? "sev-" + r.severity : "muted"}">${r.status === "FAIL" ? r.severity : "-"}</td>
      <td class="muted">${esc(r.evaluator)}</td>
    </tr>
    <tr class="detail hidden"><td colspan="5">
      <h4>Prompt</h4><pre>${esc(r.prompt)}</pre>
      <h4>Model response</h4><pre>${esc(r.response)}</pre>
      <h4>Expected behaviour</h4><pre>${esc(r.expected)}</pre>
      <h4>Evaluator reason</h4><pre>${esc(r.reason)}</pre>
    </td></tr>`).join("");
}

async function loadRun(runId) {
  const [stats, results] = await Promise.all([
    getJSON(`/api/stats?run_id=${runId}`),
    getJSON(`/api/results?run_id=${runId}`),
  ]);
  allResults = results;
  renderCards(stats);
  renderRisk(stats);
  renderCategories(stats);
  renderTable();
}

async function init() {
  try {
    const runs = await getJSON("/api/runs");
    if (!runs.length) {
      $("#empty").classList.remove("hidden");
      return;
    }
    const select = $("#run-select");
    select.innerHTML = runs.map((r) =>
      `<option value="${r.id}">Run #${r.id} - ${esc(r.started_at)}</option>`).join("");
    select.addEventListener("change", () => loadRun(select.value).catch((e) => showError(e.message)));
    await loadRun(runs[0].id);
    $("#content").classList.remove("hidden");
  } catch (e) {
    showError(e.message);
  }
}

$("#results-body").addEventListener("click", (e) => {
  const row = e.target.closest("tr.main");
  if (row) row.nextElementSibling.classList.toggle("hidden");
});

$("#filters").addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  currentFilter = btn.dataset.filter;
  document.querySelectorAll("#filters button").forEach((b) => b.classList.toggle("active", b === btn));
  renderTable();
});

init();

$("#report-btn").addEventListener("click", async () => {
  const btn = $("#report-btn");
  const status = $("#report-status");
  btn.disabled = true;
  status.textContent = "Generating report...";
  try {
    const r = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: Number($("#run-select").value),
        target_name: $("#report-target").value,
        evidence: $("#opt-evidence").checked,
        risk: $("#opt-risk").checked,
        recommendations: $("#opt-reco").checked,
        owasp: $("#opt-owasp").checked,
      }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || r.statusText);
    status.innerHTML = `Report ready: <a href="${data.url}" target="_blank">${esc(data.filename)}</a>`;
  } catch (e) {
    status.textContent = "Error: " + e.message;
  } finally {
    btn.disabled = false;
  }
});
