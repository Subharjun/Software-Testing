/* ═══════════════════════════════════════════════════════════
   QA Forge Dashboard — JavaScript
   Loads test result JSON and animates the dashboard
   ═══════════════════════════════════════════════════════════ */

// ─── Simulated test results (populated by run_all_tests.sh) ──────────────
// In a real CI run, this file is written by the test runner.
// For demo purposes, we embed realistic numbers here.

const RESULTS = {
  unit: {
    passed: 61,
    failed: 0,
    total:  61,
    coverage: 87,
  },
  integration: {
    passed: 42,
    failed: 0,
    total:  42,
  },
  e2e: {
    passed: 13,
    failed: 2,
    total:  15,
  },
  performance: {
    passed: 1,   // 1 = benchmark met (avg < 200ms), 0 = missed
    failed: 0,
    total:  1,
    avg_ms: 48,
    p95_ms: 145,
    failure_rate: "0.2%",
  },
  security: {
    passed: 32,
    failed: 0,
    total:  32,
    bandit_high: 0,
  },
  accessibility: {
    passed: 1,  // 1 = zero WCAG AA violations, 0 = violations found
    failed: 0,
    total:  1,
    violations: 0,
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────

function passRate(r) {
  return r.total > 0 ? Math.round((r.passed / r.total) * 100) : 0;
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function animateNumber(el, target, suffix = "") {
  let start = 0;
  const step = Math.ceil(target / 30);
  const timer = setInterval(() => {
    start = Math.min(start + step, target);
    el.textContent = start + suffix;
    if (start >= target) clearInterval(timer);
  }, 20);
}

// ─── Score ring (doughnut) ─────────────────────────────────────────────────

function drawScoreRing(score) {
  const canvas = document.getElementById("score-ring");
  const ctx    = canvas.getContext("2d");

  const color = score >= 90 ? "#22c55e"
              : score >= 70 ? "#eab308"
              : "#ef4444";

  new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [{
        data:             [score, 100 - score],
        backgroundColor:  [color, "rgba(255,255,255,0.04)"],
        borderWidth:      0,
        borderRadius:     6,
      }],
    },
    options: {
      cutout:    "80%",
      animation: { duration: 1200 },
      plugins:   { tooltip: { enabled: false }, legend: { display: false } },
    },
  });
}

// ─── Distribution chart ───────────────────────────────────────────────────

function drawDistChart() {
  const ctx = document.getElementById("dist-chart").getContext("2d");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Unit", "Integration", "E2E", "Performance", "Security", "Accessibility"],
      datasets: [{
        label:           "Tests",
        data:            [RESULTS.unit.total, RESULTS.integration.total, RESULTS.e2e.total, RESULTS.performance.total, RESULTS.security.total, RESULTS.accessibility.total],
        backgroundColor: ["rgba(99,102,241,0.7)", "rgba(59,130,246,0.7)", "rgba(139,92,246,0.7)", "rgba(234,179,8,0.7)", "rgba(239,68,68,0.7)", "rgba(34,197,94,0.7)"],
        borderRadius:    6,
      }],
    },
    options: {
      responsive: true,
      plugins:    { legend: { display: false } },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { size: 11 } } },
        y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { size: 11 } }, beginAtZero: true },
      },
      animation: { duration: 1000 },
    },
  });
}

// ─── Pass rate chart ──────────────────────────────────────────────────────

function drawPassChart() {
  const ctx   = document.getElementById("pass-chart").getContext("2d");
  const rates = [
    passRate(RESULTS.unit),
    passRate(RESULTS.integration),
    passRate(RESULTS.e2e),
    100,
    passRate(RESULTS.security),
    100,
  ];
  new Chart(ctx, {
    type: "bar",
    data: {
      labels:   ["Unit", "Integration", "E2E", "Perf", "Security", "A11y"],
      datasets: [{
        label: "Pass %",
        data:  rates,
        backgroundColor: rates.map(r =>
          r === 100 ? "rgba(34,197,94,0.7)" :
          r >= 80   ? "rgba(234,179,8,0.7)" :
                      "rgba(239,68,68,0.7)"
        ),
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins:    { legend: { display: false } },
      scales: {
        x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { size: 11 } } },
        y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#64748b", font: { size: 11 }, callback: v => v + "%" }, min: 0, max: 100 },
      },
      animation: { duration: 1000 },
    },
  });
}

// ─── Coverage chart ───────────────────────────────────────────────────────

function drawCovChart() {
  const ctx = document.getElementById("cov-chart").getContext("2d");
  const cov = RESULTS.unit.coverage;
  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels:   ["Covered", "Uncovered"],
      datasets: [{
        data:             [cov, 100 - cov],
        backgroundColor:  ["rgba(99,102,241,0.8)", "rgba(255,255,255,0.04)"],
        borderWidth:      0,
        borderRadius:     6,
      }],
    },
    options: {
      cutout:    "65%",
      animation: { duration: 1200 },
      plugins: {
        legend: {
          display:  true,
          position: "bottom",
          labels:   { color: "#94a3b8", font: { size: 11 }, boxWidth: 12, padding: 12 },
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.parsed}%` },
        },
      },
    },
  });
}

// ─── Layer cards ──────────────────────────────────────────────────────────

function updateLayerCard(id, dotId, barId, countId, result) {
  const rate  = passRate(result);
  const dot   = document.getElementById(dotId);
  const bar   = document.getElementById(barId);
  const count = document.getElementById(countId);

  dot.className  = "status-dot " + (rate === 100 ? "pass" : rate >= 80 ? "partial" : "fail");
  count.textContent = `${result.passed}/${result.total} passed`;

  setTimeout(() => { bar.style.width = rate + "%"; }, 200);
}

// ─── Summary banner ───────────────────────────────────────────────────────

function updateSummary() {
  const allPassed = Object.values(RESULTS).reduce((s, r) => s + r.passed, 0);
  const allFailed = Object.values(RESULTS).reduce((s, r) => s + r.failed, 0);
  const allTotal  = Object.values(RESULTS).reduce((s, r) => s + r.total,  0);
  const score     = Math.round((allPassed / allTotal) * 100);

  const totalEl  = document.getElementById("total-tests");
  const passEl   = document.getElementById("passed-tests");
  const failEl   = document.getElementById("failed-tests");
  const covEl    = document.getElementById("coverage-pct");
  const scoreEl  = document.getElementById("overall-score");

  animateNumber(totalEl, allTotal);
  animateNumber(passEl,  allPassed);
  animateNumber(failEl,  allFailed);
  animateNumber(covEl,   RESULTS.unit.coverage, "%");
  scoreEl.textContent = score + "%";

  drawScoreRing(score);

  const verdict     = document.getElementById("verdict");
  const verdictIcon = verdict.querySelector(".verdict-icon");
  const verdictText = verdict.querySelector(".verdict-text");

  if (score === 100) {
    verdictIcon.textContent = "✅";
    verdictText.textContent = "All tests passing — ship it!";
    verdictText.style.color = "#4ade80";
  } else if (score >= 85) {
    verdictIcon.textContent = "⚠️";
    verdictText.textContent = "Minor failures — review E2E";
    verdictText.style.color = "#facc15";
  } else {
    verdictIcon.textContent = "❌";
    verdictText.textContent = "Critical failures detected";
    verdictText.style.color = "#f87171";
  }
}

// ─── Boot ─────────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  updateSummary();

  updateLayerCard("unit",          "unit-dot",        "unit-bar",        "unit-count",        RESULTS.unit);
  updateLayerCard("integration",   "integration-dot", "integration-bar", "integration-count", RESULTS.integration);
  updateLayerCard("e2e",           "e2e-dot",         "e2e-bar",         "e2e-count",         RESULTS.e2e);
  updateLayerCard("performance",   "perf-dot",        "perf-bar",        "perf-count",        RESULTS.performance);
  updateLayerCard("security",      "security-dot",    "security-bar",    "security-count",    RESULTS.security);
  updateLayerCard("accessibility", "a11y-dot",        "a11y-bar",        "a11y-count",        RESULTS.accessibility);

  drawDistChart();
  drawPassChart();
  drawCovChart();
});
