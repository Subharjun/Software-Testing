# ⚗️ QA Forge — Software Testing Portfolio Project

> A full-stack Task Manager application built as a **living demonstration** of comprehensive software quality assurance across all critical testing layers.

[![CI/CD Pipeline](https://github.com/your-username/qa-forge/actions/workflows/qa-pipeline.yml/badge.svg)](https://github.com/your-username/qa-forge/actions)

---

## 🎯 What This Project Demonstrates

This is not just an app with some tests bolted on. **QA Forge** is a purposefully designed showcase where every testing domain is fully implemented on a real, working system — a REST API + web frontend — the way it would be done in a professional engineering team.

| Layer | Tool | Tests | What's Covered |
|---|---|---|---|
| 🔬 **Unit** | Pytest + pytest-cov | 60+ | Business logic, validation, utilities |
| 🔗 **Integration** | Pytest + Flask TestClient | 40+ | All REST endpoints, auth flows, error handling |
| 🖥️ **E2E** | Playwright | 15+ | Full browser user journeys, cross-browser |
| ⚡ **Performance** | Locust | Load scenarios | 50 users, response benchmarks, failure rates |
| 🔐 **Security** | Pytest + Bandit | 30+ | SQL injection, XSS, auth bypass, OWASP |
| ♿ **Accessibility** | Pa11y + axe-core | WCAG 2.1 AA | Color contrast, keyboard nav, screen reader |

---

## 🏗️ Architecture

```
QA-Forge/
├── backend/                   # 🐍 Flask REST API (System Under Test)
│   ├── app.py                 #    API endpoints, auth, routing
│   ├── models.py              #    Pure business logic (unit-testable)
│   └── requirements.txt
│
├── frontend/                  # 🌐 Task Manager Web UI
│   ├── index.html
│   ├── style.css              #    Dark glassmorphism theme
│   └── app.js
│
├── tests/
│   ├── conftest.py            # 🧩 Shared fixtures (app, client, auth)
│   ├── unit/
│   │   ├── test_models.py     #    60+ unit tests with parametrize
│   │   └── test_validation.py #    Boundary & equivalence tests
│   ├── integration/
│   │   └── test_api.py        #    40+ HTTP-level API tests
│   ├── e2e/
│   │   └── test_e2e.py        #    Playwright browser automation
│   ├── performance/
│   │   └── locustfile.py      #    Locust load test scenarios
│   ├── security/
│   │   └── test_security.py   #    OWASP-inspired security tests
│   └── accessibility/
│       └── .pa11yrc.js        #    Pa11y WCAG 2.1 AA config
│
├── qa_dashboard/              # 📊 Interactive test results dashboard
│   ├── index.html
│   ├── dashboard.css
│   └── dashboard.js
│
├── reports/                   # 📄 Auto-generated HTML reports
├── .github/workflows/
│   └── qa-pipeline.yml        # 🚦 GitHub Actions CI/CD pipeline
├── pytest.ini                 # ⚙️ Pytest configuration
└── run_all_tests.sh           # 🚀 One-command test runner
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip
- Node.js + npm (for Pa11y accessibility testing)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/qa-forge.git
cd qa-forge

# Install Python dependencies
pip install -r backend/requirements.txt

# Install Playwright browsers
playwright install chromium

# (Optional) Install Pa11y for accessibility tests
npm install -g pa11y
```

### 2. Run the App

```bash
# Terminal 1 — Backend API
python backend/app.py
# → Starts on http://localhost:5050

# Terminal 2 — Frontend
python -m http.server 8080 --directory frontend
# → Opens on http://localhost:8080
```

Login with: `tester / tester123` or `admin / admin123`

### 3. Run the Full Test Suite

```bash
bash run_all_tests.sh
```

This runs all 6 testing layers and generates HTML reports in `reports/`.

**Optional flags:**
```bash
bash run_all_tests.sh --skip-e2e   # Skip browser tests
bash run_all_tests.sh --skip-load  # Skip performance test
```

### 4. View the QA Dashboard

```bash
open qa_dashboard/index.html
```

---

## 🔬 Testing Details

### Unit Testing

Targets the pure Python functions in `backend/models.py` — no Flask, no network, no database.

**Key techniques demonstrated:**
- **Boundary Value Analysis** (BVA) — testing at exact limits (120 chars, 0, max length)
- **Equivalence Partitioning** — valid/invalid classes for status, priority, dates
- **Parametrized test batteries** — `@pytest.mark.parametrize` for concise coverage
- **TypeError/ValueError** negative path testing
- **Code coverage enforcement** — minimum 75%

```bash
pytest tests/unit/ -v --cov=backend --cov-report=html:reports/coverage_html
```

### Integration Testing

Tests the full HTTP layer using Flask's test client. Database is in-memory SQLite per session.

**Key techniques:**
- **Fixture-based state** — `conftest.py` provides scoped `app`, `client`, `auth_headers`
- **CRUD contract verification** — every status code is asserted
- **Ownership isolation** — tester cannot see admin's tasks
- **Error contract testing** — 400, 401, 404, 422 all verified

```bash
pytest tests/integration/ -v
```

### End-to-End Testing

Playwright drives a real Chromium browser through the complete user journey.

**What's tested:**
- Login form validation and auth flow
- Task creation, update, deletion via UI
- Search and filter interactions
- Error state rendering
- Basic accessibility (labels on inputs)

```bash
pytest tests/e2e/ --headed  # Watch in browser
```

### Performance Testing

Locust simulates realistic user load with weighted task distribution.

- `TaskManagerUser` (weight 4): mainly read-heavy operations
- `AdminUser` (weight 1): heavier write operations
- Produces a detailed HTML performance report

```bash
# Interactive UI
locust -f tests/performance/locustfile.py --host http://localhost:5050

# Headless CI run
locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 60s \
       --host http://localhost:5050 --html reports/performance_report.html
```

### Security Testing

OWASP Top-10 inspired test battery:

| Attack Vector | How Tested |
|---|---|
| SQL Injection | 8 payloads in title, search, and login |
| XSS | Script tags stored/retrieved safely; response is always JSON |
| Auth Bypass | No token, tampered signature, `none` algorithm exploit |
| Sensitive Data | Passwords not exposed in responses; ownership isolation |
| DoS / Large Payloads | 10,000-char title correctly rejected (4xx, not 500) |

```bash
pytest tests/security/ -v
bandit -r backend/ -ll           # Static analysis
```

### Accessibility Testing

```bash
# Run Pa11y against live frontend
pa11y --config tests/accessibility/.pa11yrc.js http://localhost:8080
```

Checks WCAG 2.1 AA compliance including:
- Color contrast ratios
- Form labels associated with inputs
- Keyboard navigability
- ARIA attributes
- Heading hierarchy

---

## 📊 Reports

All reports are auto-generated into `reports/`:

| Report | Tool | Command |
|---|---|---|
| `unit_report.html` | pytest-html | `pytest tests/unit/` |
| `coverage_html/` | pytest-cov | `--cov-report=html` |
| `integration_report.html` | pytest-html | `pytest tests/integration/` |
| `e2e_report.html` | pytest-html | `pytest tests/e2e/` |
| `performance_report.html` | Locust | `locust --html` |
| `security_report.html` | pytest-html | `pytest tests/security/` |
| `bandit_report.txt` | Bandit | `bandit -r backend/` |
| `a11y_report.html` | Pa11y | `pa11y --reporter html` |

---

## 🚦 CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/qa-pipeline.yml`) runs on every push/PR:

```
push/PR
  │
  ├─ Job 1: Unit + Integration + Security  ──► artifacts: reports/
  │
  ├─ Job 2: E2E (Playwright)               ──► artifacts: e2e_report.html
  │
  ├─ Job 3: Performance (Locust 20 users)  ──► artifacts: performance_report.html
  │
  └─ Job 4: Quality Gate (blocks PR if Job 1 fails)
```

---

## 🧪 Testing Concepts Demonstrated

| Concept | Where |
|---|---|
| Black-box testing | Integration & security tests |
| White-box testing | Unit tests with coverage |
| Regression testing | Full suite on every commit |
| Smoke testing | Health check endpoint |
| Negative testing | All 422/401/404 validation |
| Boundary value analysis | `test_validation.py` |
| Equivalence partitioning | Status/priority enum tests |
| State transition testing | `test_models.py::TestStatusTransitions` |
| Parametrized tests | `@pytest.mark.parametrize` batteries |
| Test fixtures | `conftest.py` |
| Mocking (implicit) | In-memory DB isolates from disk |
| Load testing | Locust scenarios |
| Stress testing | Max oversized payload tests |
| Static analysis | Bandit |
| WCAG compliance | Pa11y / axe-core |

---

## 📄 License

MIT — free to use as a portfolio reference.

---

*Built with ⚗️ to showcase real-world software testing practices across the full quality assurance spectrum.*
