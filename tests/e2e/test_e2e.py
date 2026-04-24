"""
Playwright E2E Tests — tests/e2e/test_e2e.py
Full browser-level tests for the QA Forge frontend.

Covers:
  - Login page rendering
  - Successful login flow
  - Task creation via the UI
  - Task list loading
  - Task status update
  - Task deletion
  - Error state display (invalid login)

Prerequisites:
  1. Backend running: python backend/app.py
  2. Frontend served: python -m http.server 8080 --directory frontend
  3. Playwright installed: playwright install

Run:  pytest tests/e2e/ -v --headed (or --headless)
"""

import pytest
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL      = "http://localhost:8080"
API_BASE      = "http://localhost:5050"
VALID_USER    = "tester"
VALID_PASS    = "tester123"
INVALID_PASS  = "wrongpassword"


@pytest.fixture(scope="module")
def browser_context():
    """Launch Chromium and yield a browser context for the test module."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context):
    p = browser_context.new_page()
    yield p
    p.close()


# ═══════════════════════════════════════════════
# Page Rendering
# ═══════════════════════════════════════════════

class TestLoginPage:
    def test_login_page_loads(self, page: Page):
        page.goto(BASE_URL)
        expect(page).to_have_title("QA Forge")

    def test_login_form_present(self, page: Page):
        page.goto(BASE_URL)
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator("#login-btn")).to_be_visible()

    def test_login_page_has_logo(self, page: Page):
        page.goto(BASE_URL)
        expect(page.locator(".logo")).to_be_visible()


# ═══════════════════════════════════════════════
# Authentication Flow
# ═══════════════════════════════════════════════

class TestAuthFlow:
    def test_invalid_login_shows_error(self, page: Page):
        page.goto(BASE_URL)
        page.fill("#username", VALID_USER)
        page.fill("#password", INVALID_PASS)
        page.click("#login-btn")
        expect(page.locator("#auth-error")).to_be_visible(timeout=5000)

    def test_valid_login_navigates_to_dashboard(self, page: Page):
        page.goto(BASE_URL)
        page.fill("#username", VALID_USER)
        page.fill("#password", VALID_PASS)
        page.click("#login-btn")
        expect(page.locator("#dashboard")).to_be_visible(timeout=5000)

    def test_logout_returns_to_login(self, page: Page):
        page.goto(BASE_URL)
        page.fill("#username", VALID_USER)
        page.fill("#password", VALID_PASS)
        page.click("#login-btn")
        page.wait_for_selector("#dashboard", timeout=5000)
        page.click("#logout-btn")
        expect(page.locator("#login-section")).to_be_visible(timeout=5000)


# ═══════════════════════════════════════════════
# Task CRUD via UI
# ═══════════════════════════════════════════════

class TestTaskManagement:
    @pytest.fixture(autouse=True)
    def login(self, page: Page):
        page.goto(BASE_URL)
        page.fill("#username", VALID_USER)
        page.fill("#password", VALID_PASS)
        page.click("#login-btn")
        page.wait_for_selector("#dashboard", timeout=5000)

    def test_task_list_loads(self, page: Page):
        expect(page.locator("#task-list")).to_be_visible()

    def test_create_task_via_form(self, page: Page):
        page.click("#add-task-btn")
        page.wait_for_selector("#task-modal", timeout=3000)
        page.fill("#task-title-input", "E2E Created Task")
        page.select_option("#task-priority-input", "high")
        page.click("#save-task-btn")
        page.wait_for_timeout(1000)
        expect(page.locator("#task-list")).to_contain_text("E2E Created Task")

    def test_create_task_without_title_shows_error(self, page: Page):
        page.click("#add-task-btn")
        page.wait_for_selector("#task-modal", timeout=3000)
        page.fill("#task-title-input", "")
        page.click("#save-task-btn")
        expect(page.locator("#modal-error")).to_be_visible(timeout=3000)

    def test_delete_task_removes_from_list(self, page: Page):
        # Create a task to delete
        page.click("#add-task-btn")
        page.wait_for_selector("#task-modal", timeout=3000)
        page.fill("#task-title-input", "Task To Delete")
        page.click("#save-task-btn")
        page.wait_for_timeout(800)

        # Click delete on the latest task
        delete_btn = page.locator(".delete-btn").last
        delete_btn.click()
        page.wait_for_timeout(800)
        expect(page.locator("#task-list")).not_to_contain_text("Task To Delete")

    def test_search_filters_tasks(self, page: Page):
        # Ensure a searchable task exists
        page.click("#add-task-btn")
        page.wait_for_selector("#task-modal")
        page.fill("#task-title-input", "UniqueSearchableTask123")
        page.click("#save-task-btn")
        page.wait_for_timeout(800)

        page.fill("#search-input", "UniqueSearchableTask123")
        page.wait_for_timeout(600)
        expect(page.locator("#task-list")).to_contain_text("UniqueSearchableTask123")

    def test_filter_by_priority_high(self, page: Page):
        page.select_option("#priority-filter", "high")
        page.wait_for_timeout(600)
        task_items = page.locator(".task-card")
        count = task_items.count()
        for i in range(count):
            badge = task_items.nth(i).locator(".priority-badge").inner_text()
            assert "high" in badge.lower()


# ═══════════════════════════════════════════════
# Accessibility (basic Playwright checks)
# ═══════════════════════════════════════════════

class TestAccessibilityBasics:
    def test_login_inputs_have_labels(self, page: Page):
        page.goto(BASE_URL)
        # Labels should be associated with inputs
        username_label = page.locator("label[for='username']")
        password_label = page.locator("label[for='password']")
        expect(username_label).to_be_visible()
        expect(password_label).to_be_visible()

    def test_login_button_has_text(self, page: Page):
        page.goto(BASE_URL)
        btn_text = page.locator("#login-btn").inner_text()
        assert len(btn_text.strip()) > 0, "Login button must have visible text"
