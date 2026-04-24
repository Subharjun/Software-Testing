"""
Unit Tests — tests/unit/test_validation.py
Tests for the validate_task_payload() function in backend/app.py.

Covers:
  - Required-field enforcement
  - Length boundary conditions
  - Status / priority enum validation
  - Date format validation
  - Combined multi-field scenarios
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app import validate_task_payload


class TestValidateTaskPayload:
    # ── Title ─────────────────────────────────────────────────────────────

    def test_missing_title_when_required_produces_error(self):
        errors, _ = validate_task_payload({}, require_title=True)
        assert any("title" in e for e in errors)

    def test_missing_title_not_required_is_ok(self):
        errors, _ = validate_task_payload({}, require_title=False)
        assert errors == []

    def test_title_at_max_length_accepted(self):
        errors, _ = validate_task_payload({"title": "x" * 120})
        assert errors == []

    def test_title_over_max_length_rejected(self):
        errors, _ = validate_task_payload({"title": "x" * 121})
        assert any("title" in e for e in errors)

    def test_blank_title_required_mode_produces_error(self):
        errors, _ = validate_task_payload({"title": "   "}, require_title=True)
        assert any("title" in e for e in errors)

    def test_valid_title_in_cleaned(self):
        _, cleaned = validate_task_payload({"title": "  My Task  "})
        assert cleaned["title"] == "My Task"

    # ── Description ───────────────────────────────────────────────────────

    def test_description_at_max_accepted(self):
        errors, _ = validate_task_payload({"title": "T", "description": "d" * 1000})
        assert errors == []

    def test_description_over_max_rejected(self):
        errors, _ = validate_task_payload({"title": "T", "description": "d" * 1001})
        assert any("description" in e for e in errors)

    # ── Status ────────────────────────────────────────────────────────────

    @pytest.mark.parametrize("status", ["todo", "in_progress", "done", "archived"])
    def test_valid_statuses_accepted(self, status):
        errors, cleaned = validate_task_payload({"title": "T", "status": status})
        assert errors == []
        assert cleaned["status"] == status

    def test_invalid_status_produces_error(self):
        errors, _ = validate_task_payload({"title": "T", "status": "pending"})
        assert any("status" in e for e in errors)

    # ── Priority ──────────────────────────────────────────────────────────

    @pytest.mark.parametrize("priority", ["low", "medium", "high", "critical"])
    def test_valid_priorities_accepted(self, priority):
        errors, cleaned = validate_task_payload({"title": "T", "priority": priority})
        assert errors == []
        assert cleaned["priority"] == priority

    def test_invalid_priority_produces_error(self):
        errors, _ = validate_task_payload({"title": "T", "priority": "urgent"})
        assert any("priority" in e for e in errors)

    # ── Due Date ──────────────────────────────────────────────────────────

    def test_valid_due_date_accepted(self):
        errors, cleaned = validate_task_payload({"title": "T", "due_date": "2025-12-31"})
        assert errors == []
        assert cleaned["due_date"] == "2025-12-31"

    @pytest.mark.parametrize("bad_date", [
        "31-12-2025",
        "2025/12/31",
        "December 31 2025",
        "2025-13-01",
        "not-a-date",
    ])
    def test_invalid_due_date_formats_rejected(self, bad_date):
        errors, _ = validate_task_payload({"title": "T", "due_date": bad_date})
        assert any("due_date" in e for e in errors)

    def test_empty_due_date_string_accepted(self):
        errors, _ = validate_task_payload({"title": "T", "due_date": ""})
        assert errors == []

    # ── Tags ──────────────────────────────────────────────────────────────

    def test_tags_at_max_accepted(self):
        errors, _ = validate_task_payload({"title": "T", "tags": "t" * 200})
        assert errors == []

    def test_tags_over_max_rejected(self):
        errors, _ = validate_task_payload({"title": "T", "tags": "t" * 201})
        assert any("tags" in e for e in errors)

    # ── Multi-error collection ─────────────────────────────────────────────

    def test_multiple_validation_errors_collected(self):
        errors, _ = validate_task_payload({
            "title":    "x" * 121,
            "status":   "bad_status",
            "priority": "bad_priority",
        })
        assert len(errors) >= 3

    def test_valid_full_payload_no_errors(self):
        errors, cleaned = validate_task_payload({
            "title":       "Deploy microservice",
            "description": "Run full CI pipeline before deploying",
            "status":      "in_progress",
            "priority":    "high",
            "due_date":    "2025-08-15",
            "tags":        "devops,ci,prod",
        })
        assert errors == []
        assert cleaned["title"] == "Deploy microservice"
