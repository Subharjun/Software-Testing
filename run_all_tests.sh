#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  QA Forge — Master Test Runner
#  Runs all testing layers and generates HTML reports.
#
#  Usage:
#    bash run_all_tests.sh              # full suite
#    bash run_all_tests.sh --skip-e2e  # skip E2E (no browser needed)
#    bash run_all_tests.sh --skip-load # skip performance load test
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

SKIP_E2E=false
SKIP_LOAD=false
for arg in "$@"; do
  [[ "$arg" == "--skip-e2e"  ]] && SKIP_E2E=true
  [[ "$arg" == "--skip-load" ]] && SKIP_LOAD=true
done

PASS=0; FAIL=0; SKIPPED=0

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════╗${RESET}"
  printf "${CYAN}${BOLD}║  %-36s║${RESET}\n" "$1"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════╝${RESET}"
}

run_step() {
  local label="$1"; shift
  echo -e "\n${BOLD}▶ ${label}${RESET}"
  if "$@"; then
    echo -e "${GREEN}✔ ${label} — PASSED${RESET}"
    (( PASS++ )) || true
  else
    echo -e "${RED}✖ ${label} — FAILED${RESET}"
    (( FAIL++ )) || true
    return 0   # don't abort; continue remaining steps
  fi
}

skip_step() {
  echo -e "\n${YELLOW}⏭ Skipping: $1${RESET}"
  (( SKIPPED++ )) || true
}

# ─── Setup ──────────────────────────────────────────────────────────────────
banner "QA Forge — Full Test Suite"
mkdir -p reports

echo -e "\n${BOLD}Environment check...${RESET}"
python3 --version
pip show flask pytest locust 2>/dev/null | grep "^Name:" || echo "(some packages may not be installed)"

# ─── 1. Unit Tests ──────────────────────────────────────────────────────────
banner "1 / 6  Unit Tests"
run_step "Unit tests (pytest-cov)" \
  pytest tests/unit/ \
    --cov=backend/models \
    --cov=backend/app \
    --cov-report=html:reports/coverage_html \
    --cov-report=term-missing \
    --cov-fail-under=75 \
    --html=reports/unit_report.html \
    --self-contained-html \
    -q

# ─── 2. Integration Tests ───────────────────────────────────────────────────
banner "2 / 6  Integration Tests"
run_step "Integration tests" \
  pytest tests/integration/ \
    --html=reports/integration_report.html \
    --self-contained-html \
    -q

# ─── 3. Security Tests ──────────────────────────────────────────────────────
banner "3 / 6  Security Tests"
run_step "Security tests (OWASP)" \
  pytest tests/security/ \
    --html=reports/security_report.html \
    --self-contained-html \
    -q

# Static analysis with Bandit
echo -e "\n${BOLD}▶ Bandit static security analysis${RESET}"
if command -v bandit &> /dev/null; then
  bandit -r backend/ -ll -f txt -o reports/bandit_report.txt 2>&1 || true
  bandit -r backend/ -ll --exit-zero && echo -e "${GREEN}✔ Bandit — no high-severity issues${RESET}" || echo -e "${YELLOW}⚠ Bandit — check reports/bandit_report.txt${RESET}"
else
  echo -e "${YELLOW}  bandit not installed — skipping static analysis${RESET}"
fi

# ─── 4. E2E Tests ───────────────────────────────────────────────────────────
banner "4 / 6  End-to-End Tests"
if [ "$SKIP_E2E" = true ]; then
  skip_step "E2E tests (--skip-e2e flag set)"
else
  # Check if backend is running
  if curl -sf http://localhost:5050/health > /dev/null 2>&1; then
    run_step "E2E tests (Playwright)" \
      pytest tests/e2e/ \
        --html=reports/e2e_report.html \
        --self-contained-html \
        -q
  else
    echo -e "${YELLOW}  ⚠ Backend not running on :5050 — start with: python backend/app.py${RESET}"
    echo -e "${YELLOW}  ⚠ Frontend not served — start with: python -m http.server 8080 --directory frontend${RESET}"
    skip_step "E2E tests (backend/frontend not running)"
  fi
fi

# ─── 5. Performance Tests ───────────────────────────────────────────────────
banner "5 / 6  Performance Tests"
if [ "$SKIP_LOAD" = true ]; then
  skip_step "Performance tests (--skip-load flag set)"
elif ! command -v locust &> /dev/null; then
  echo -e "${YELLOW}  locust not installed — skipping load test${RESET}"
  skip_step "Performance tests (locust missing)"
elif ! curl -sf http://localhost:5050/health > /dev/null 2>&1; then
  echo -e "${YELLOW}  Backend not running — skipping load test${RESET}"
  skip_step "Performance tests (backend not running)"
else
  run_step "Performance / load test (50 users, 30s)" \
    locust -f tests/performance/locustfile.py \
      --headless \
      -u 50 -r 10 -t 30s \
      --host http://localhost:5050 \
      --html reports/performance_report.html \
      --exit-code-on-error 1
fi

# ─── 6. Accessibility Tests ─────────────────────────────────────────────────
banner "6 / 6  Accessibility Tests"
if command -v pa11y &> /dev/null && curl -sf http://localhost:8080 > /dev/null 2>&1; then
  run_step "Accessibility (Pa11y WCAG2AA)" \
    pa11y --config tests/accessibility/.pa11yrc.js \
      --reporter html \
      http://localhost:8080 \
      > reports/a11y_report.html 2>&1
else
  echo -e "${YELLOW}  Install pa11y with: npm install -g pa11y${RESET}"
  echo -e "${YELLOW}  And serve frontend: python -m http.server 8080 --directory frontend${RESET}"
  skip_step "Accessibility tests (pa11y or frontend not available)"
fi

# ─── Final Summary ──────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       QA FORGE RESULTS           ║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════╣${RESET}"
echo -e "${BOLD}║  ${GREEN}✔ Passed : ${PASS}${RESET}${BOLD}                    ║${RESET}"
echo -e "${BOLD}║  ${RED}✖ Failed : ${FAIL}${RESET}${BOLD}                    ║${RESET}"
echo -e "${BOLD}║  ${YELLOW}⏭ Skipped: ${SKIPPED}${RESET}${BOLD}                    ║${RESET}"
echo -e "${BOLD}╠══════════════════════════════════╣${RESET}"
echo -e "${BOLD}║  Reports → ./reports/            ║${RESET}"
echo -e "${BOLD}║  Dashboard → qa_dashboard/       ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════╝${RESET}"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo -e "${RED}${BOLD}⚠  ${FAIL} test stage(s) failed. Check reports/ for details.${RESET}"
  exit 1
else
  echo -e "${GREEN}${BOLD}🎉 All test stages passed!${RESET}"
  exit 0
fi
