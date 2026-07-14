const state = {
  scenarios: [],
  activeIndex: 0,
  activeTab: "alert",
  activeMetric: "",
};

const els = {
  picker: document.querySelector("#scenario-picker"),
  incidentId: document.querySelector("#incident-id"),
  severity: document.querySelector("#severity"),
  service: document.querySelector("#incident-service"),
  title: document.querySelector("#incident-title"),
  summary: document.querySelector("#incident-summary"),
  impact: document.querySelector("#incident-impact"),
  evidenceCount: document.querySelector("#evidence-count"),
  evidenceView: document.querySelector("#evidence-view"),
  tabs: [...document.querySelectorAll("[data-tab]")],
  rca: document.querySelector("#rca-input"),
  draftCount: document.querySelector("#draft-count"),
  loadStrong: document.querySelector("#load-strong"),
  loadFooled: document.querySelector("#load-fooled"),
  clear: document.querySelector("#clear-rca"),
  score: document.querySelector("#score-button"),
  scoreStatus: document.querySelector("#score-status"),
  scoreDeck: document.querySelector("#score-deck"),
  overall: document.querySelector("#overall-value"),
  verdict: document.querySelector("#score-verdict"),
  missingEvidence: document.querySelector("#missing-evidence"),
  redHerrings: document.querySelector("#red-herrings"),
  groundTruth: document.querySelector("#ground-truth"),
};

function currentScenario() {
  return state.scenarios[state.activeIndex];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function compactTime(value) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(value));
}

function renderPicker() {
  els.picker.replaceChildren();
  state.scenarios.forEach((scenario, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.setAttribute("aria-selected", String(index === state.activeIndex));
    button.innerHTML = `<span>0${index + 1} / ${escapeHtml(scenario.definition.severity)}</span><strong>${escapeHtml(scenario.definition.title)}</strong>`;
    button.addEventListener("click", () => selectScenario(index));
    els.picker.append(button);
  });
}

function selectScenario(index) {
  state.activeIndex = index;
  state.activeTab = "alert";
  const scenario = currentScenario();
  state.activeMetric = scenario.definition.signals[0].name;
  els.rca.value = "";
  updateWordCount();
  resetScore();
  renderPicker();
  renderIncident();
}

function renderIncident() {
  const scenario = currentScenario();
  const definition = scenario.definition;
  els.incidentId.textContent = scenario.manifest.incident_id.toUpperCase();
  els.severity.textContent = definition.severity;
  els.service.textContent = definition.service.toUpperCase();
  els.title.textContent = definition.title;
  els.summary.textContent = definition.summary;
  els.impact.textContent = definition.impact;
  els.groundTruth.textContent = definition.root_cause;
  const total = 1 + scenario.metrics.length + scenario.logs.length + scenario.traces.length + 1;
  els.evidenceCount.textContent = `${total} ITEMS`;
  els.tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === state.activeTab)));
  renderEvidence();
}

function renderEvidence() {
  const renderers = {
    alert: renderAlert,
    metrics: renderMetrics,
    logs: renderLogs,
    traces: renderTraces,
    runbook: renderRunbook,
  };
  renderers[state.activeTab]();
}

function renderAlert() {
  const { alert, definition, manifest } = currentScenario();
  const entries = [
    ["Incident ID", alert.incident_id],
    ["Started UTC", alert.started_at.replace("T", " ").replace("+00:00", "")],
    ["Affected service", alert.service],
    ["Severity", alert.severity],
    ["Environment", alert.labels.environment],
    ["Scenario seed", manifest.seed],
  ];
  els.evidenceView.innerHTML = `
    <div class="alert-grid">
      <div class="datum wide"><span>Pager summary</span><strong>${escapeHtml(alert.summary)}</strong></div>
      ${entries.map(([label, value]) => `<div class="datum"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
      <div class="datum wide"><span>Tags</span><strong>${definition.tags.map(escapeHtml).join(" · ")}</strong></div>
    </div>`;
}

function renderMetrics() {
  const scenario = currentScenario();
  const names = [...new Set(scenario.metrics.map((row) => row.metric))];
  if (!names.includes(state.activeMetric)) state.activeMetric = names[0];
  els.evidenceView.innerHTML = `
    <div class="metric-chart"><canvas id="metric-canvas" width="900" height="430" aria-label="Selected metric timeline"></canvas></div>
    <div class="metric-legend">${names.map((name) => `<button type="button" data-metric="${escapeHtml(name)}" class="${name === state.activeMetric ? "active" : ""}">${escapeHtml(name)}</button>`).join("")}</div>`;
  els.evidenceView.querySelectorAll("[data-metric]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeMetric = button.dataset.metric;
      renderMetrics();
    });
  });
  drawMetricChart();
}

function drawMetricChart() {
  const canvas = document.querySelector("#metric-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const rows = currentScenario().metrics.filter((row) => row.metric === state.activeMetric);
  const values = rows.map((row) => Number(row.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(600, Math.floor(rect.width * dpr));
  canvas.height = Math.floor(215 * dpr);
  ctx.scale(dpr, dpr);
  const width = canvas.width / dpr;
  const height = canvas.height / dpr;
  const pad = { x: 38, top: 24, bottom: 28 };
  const plotHeight = height - pad.top - pad.bottom;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(237,240,232,.12)";
  ctx.fillStyle = "rgba(237,240,232,.46)";
  ctx.font = "9px DM Mono";
  for (let i = 0; i < 4; i += 1) {
    const y = pad.top + (plotHeight * i) / 3;
    ctx.beginPath();
    ctx.moveTo(pad.x, y);
    ctx.lineTo(width - 12, y);
    ctx.stroke();
    const label = max - (range * i) / 3;
    ctx.fillText(label.toFixed(label < 1 ? 3 : 0), 0, y + 3);
  }
  const points = values.map((value, index) => ({
    x: pad.x + ((width - pad.x - 12) * index) / Math.max(values.length - 1, 1),
    y: pad.top + plotHeight - ((value - min) / range) * plotHeight,
  }));
  const gradient = ctx.createLinearGradient(0, pad.top, 0, height);
  gradient.addColorStop(0, "rgba(217,255,63,.28)");
  gradient.addColorStop(1, "rgba(217,255,63,0)");
  ctx.beginPath();
  points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.lineTo(points.at(-1).x, height - pad.bottom);
  ctx.lineTo(points[0].x, height - pad.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();
  ctx.beginPath();
  points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.strokeStyle = "#d9ff3f";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "rgba(237,240,232,.55)";
  ctx.fillText(compactTime(rows[0].timestamp), pad.x, height - 8);
  ctx.textAlign = "right";
  ctx.fillText(compactTime(rows.at(-1).timestamp), width - 12, height - 8);
  ctx.textAlign = "left";
}

function renderLogs() {
  const rows = currentScenario().logs;
  els.evidenceView.innerHTML = rows.map((row) => `
    <div class="log-row ${row.level === "ERROR" ? "error" : ""}">
      <time>${compactTime(row.timestamp)} UTC</time>
      <b>${escapeHtml(row.level)} · ${escapeHtml(row.service)}</b>
      <span>${escapeHtml(row.message)}</span>
    </div>`).join("");
}

function renderTraces() {
  const rows = currentScenario().traces;
  els.evidenceView.innerHTML = rows.map((row) => `
    <div class="trace-row ${row.status === "ERROR" ? "error" : ""}">
      <span>${escapeHtml(row.trace_id.slice(0, 10))}</span>
      <strong>${escapeHtml(row.service)} / ${escapeHtml(row.operation)}</strong>
      <b>${escapeHtml(row.duration_ms)} ms</b>
      <span>${escapeHtml(row.status)}</span>
    </div>`).join("");
}

function renderRunbook() {
  const scenario = currentScenario();
  const steps = scenario.runbook
    .replace(/ before /i, ", before ")
    .split(/,| and /)
    .map((step) => step.trim().replace(/\.$/, ""))
    .filter(Boolean);
  els.evidenceView.innerHTML = `
    <div class="runbook-view">
      <span>OPERATOR RUNBOOK / ${escapeHtml(scenario.definition.service.toUpperCase())}</span>
      <p>${escapeHtml(scenario.runbook)}</p>
      <div class="runbook-steps">${steps.map((step, index) => `<div><b>0${index + 1}</b><span>${escapeHtml(step)}</span></div>`).join("")}</div>
    </div>`;
}

function normalize(text) {
  return String(text).toLowerCase().match(/[a-z0-9]+/g)?.join(" ") || "";
}

function contains(normalizedText, term) {
  if (!term) return false;
  const normalizedTerm = normalize(term);
  if (normalizedText.includes(normalizedTerm)) return true;
  const words = normalizedTerm.match(/[a-z0-9]+/g) || [];
  if (!words.length) return false;
  const haystack = ` ${normalizedText} `;
  const matches = words.filter((word) => haystack.includes(` ${word} `)).length;
  return matches / words.length >= 0.72;
}

function termScore(text, terms) {
  if (!terms.length) return 0;
  return terms.filter((term) => contains(text, term)).length / terms.length;
}

function scoreReport(report, truth) {
  const text = normalize(report);
  const evidenceItems = truth.expected_signals.map((signal) => [
    signal.name,
    [signal.name, signal.expected, signal.query],
  ]);
  const rootCause = termScore(text, truth.root_cause_terms);
  const evidence = evidenceItems.filter(([, terms]) => terms.some((term) => contains(text, term))).length / evidenceItems.length;
  const remediation = termScore(text, truth.remediation_terms);
  const serviceIdentification = contains(text, truth.service) ? 1 : 0;
  const triggeredRedHerrings = truth.red_herring_terms.filter((term) => contains(text, term));
  const redHerringPenalty = Math.min(0.28, 0.09 * triggeredRedHerrings.length);
  const redHerringResistance = Math.max(0, 1 - redHerringPenalty);
  const overall = Math.max(0, Math.min(1,
    rootCause * 0.42 + evidence * 0.34 + remediation * 0.14 + serviceIdentification * 0.10 - redHerringPenalty
  ));
  return {
    root_cause: rootCause,
    evidence,
    remediation,
    service_identification: serviceIdentification,
    red_herring_resistance: redHerringResistance,
    overall,
    missing_evidence: evidenceItems.filter(([, terms]) => !terms.some((term) => contains(text, term))).map(([name]) => name),
    triggered_red_herrings: triggeredRedHerrings,
  };
}

function scoreVerdict(value) {
  if (value >= .85) return "INCIDENT-READY";
  if (value >= .65) return "PROMISING — GAPS REMAIN";
  if (value >= .4) return "WEAK EVIDENCE CHAIN";
  return "FAILED INVESTIGATION";
}

function animateOverall(target) {
  const start = performance.now();
  const duration = 720;
  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    els.overall.textContent = `${Math.round(target * eased)}%`;
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function renderScore(result) {
  els.scoreDeck.classList.add("scored");
  animateOverall(result.overall * 100);
  els.verdict.textContent = scoreVerdict(result.overall);
  document.querySelectorAll("[data-score]").forEach((row) => {
    const value = result[row.dataset.score];
    row.querySelector("b i").style.width = `${Math.round(value * 100)}%`;
    row.querySelector("strong").textContent = `${Math.round(value * 100)}%`;
  });
  renderChips(els.missingEvidence, result.missing_evidence, "NO EVIDENCE GAPS", true);
  renderChips(els.redHerrings, result.triggered_red_herrings, "NO RED HERRINGS TRIGGERED", true);
  els.scoreStatus.textContent = `Scored locally against ${currentScenario().manifest.incident_id}. No report text left this browser.`;
}

function renderChips(container, items, emptyMessage, goodWhenEmpty) {
  container.replaceChildren();
  if (!items.length) {
    const chip = document.createElement("b");
    chip.className = goodWhenEmpty ? "ok" : "";
    chip.textContent = emptyMessage;
    container.append(chip);
    return;
  }
  items.forEach((item) => {
    const chip = document.createElement("b");
    chip.textContent = item;
    container.append(chip);
  });
}

function runScore() {
  const report = els.rca.value.trim();
  if (!report) {
    els.scoreStatus.textContent = "Write an RCA or load an example before scoring.";
    els.rca.focus();
    return;
  }
  els.scoreStatus.textContent = "Matching root cause, evidence, remediation, service, and red-herring terms…";
  const result = scoreReport(report, currentScenario().ground_truth);
  window.setTimeout(() => renderScore(result), 260);
}

function resetScore() {
  els.scoreDeck.classList.remove("scored");
  els.overall.textContent = "—";
  els.verdict.textContent = "AWAITING RCA";
  els.scoreStatus.textContent = "No report scored yet.";
  document.querySelectorAll("[data-score]").forEach((row) => {
    row.querySelector("b i").style.width = "0";
    row.querySelector("strong").textContent = "—";
  });
  els.missingEvidence.innerHTML = "<i>Score a report to inspect gaps.</i>";
  els.redHerrings.innerHTML = "<i>Score a report to inspect penalties.</i>";
}

function updateWordCount() {
  const words = els.rca.value.trim().match(/\S+/g)?.length || 0;
  els.draftCount.textContent = `${words} WORD${words === 1 ? "" : "S"}`;
}

els.tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    state.activeTab = tab.dataset.tab;
    els.tabs.forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
    renderEvidence();
  });
});
els.rca.addEventListener("input", updateWordCount);
els.loadStrong.addEventListener("click", () => {
  els.rca.value = currentScenario().examples.strong;
  updateWordCount();
  resetScore();
});
els.loadFooled.addEventListener("click", () => {
  els.rca.value = currentScenario().examples.fooled;
  updateWordCount();
  resetScore();
});
els.clear.addEventListener("click", () => {
  els.rca.value = "";
  updateWordCount();
  resetScore();
  els.rca.focus();
});
els.score.addEventListener("click", runScore);
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    runScore();
  }
});
window.addEventListener("resize", () => {
  if (state.activeTab === "metrics") drawMetricChart();
});

fetch("data/scenarios.json?v=20260714")
  .then((response) => {
    if (!response.ok) throw new Error("Scenario fixtures unavailable");
    return response.json();
  })
  .then((data) => {
    state.scenarios = data;
    state.activeMetric = data[0].definition.signals[0].name;
    renderPicker();
    renderIncident();
  })
  .catch((error) => {
    els.title.textContent = "The incident bundle could not be loaded.";
    els.summary.textContent = error.message;
    els.scoreStatus.textContent = "Refresh the page to retry.";
  });
