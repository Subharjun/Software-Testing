"""
Business logic / utility functions — fully unit-testable in isolation.
These are pure functions with no framework dependencies.
"""

import re
import datetime
from typing import Optional


# ─────────────────────────────────────────────
# Priority scoring
# ─────────────────────────────────────────────

PRIORITY_WEIGHTS = {
    "critical": 4,
    "high":     3,
    "medium":   2,
    "low":      1,
}


def get_priority_score(priority: str) -> int:
    """Return numeric weight for a priority string."""
    if not isinstance(priority, str):
        raise TypeError("priority must be a string")
    return PRIORITY_WEIGHTS.get(priority.lower(), 0)


def sort_tasks_by_priority(tasks: list[dict]) -> list[dict]:
    """Return tasks sorted highest-priority-first."""
    return sorted(tasks, key=lambda t: PRIORITY_WEIGHTS.get(t.get("priority", ""), 0), reverse=True)


# ─────────────────────────────────────────────
# Due-date helpers
# ─────────────────────────────────────────────

def is_overdue(due_date_str: str, reference: Optional[datetime.date] = None) -> bool:
    """Return True if due_date_str (YYYY-MM-DD) is before today/reference."""
    if not due_date_str:
        return False
    ref = reference or datetime.date.today()
    try:
        due = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {due_date_str!r}. Expected YYYY-MM-DD.")
    return due < ref


def days_until_due(due_date_str: str, reference: Optional[datetime.date] = None) -> Optional[int]:
    """Return number of days until due date (negative if overdue). None if no date."""
    if not due_date_str:
        return None
    ref = reference or datetime.date.today()
    try:
        due = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format: {due_date_str!r}")
    return (due - ref).days


# ─────────────────────────────────────────────
# Tag helpers
# ─────────────────────────────────────────────

def parse_tags(tags_str: str) -> list[str]:
    """Convert comma-separated tags string to sorted, deduplicated list."""
    if not tags_str or not isinstance(tags_str, str):
        return []
    tags = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
    return sorted(set(tags))


def tags_match(task_tags_str: str, filter_tags: list[str]) -> bool:
    """Return True if task has ALL filter_tags."""
    task_tags = set(parse_tags(task_tags_str))
    return all(t.lower() in task_tags for t in filter_tags)


# ─────────────────────────────────────────────
# Title sanitisation
# ─────────────────────────────────────────────

_MULTI_SPACE = re.compile(r"\s+")


def sanitise_title(title: str) -> str:
    """Collapse whitespace and strip leading/trailing spaces."""
    if not isinstance(title, str):
        raise TypeError("title must be a string")
    return _MULTI_SPACE.sub(" ", title).strip()


# ─────────────────────────────────────────────
# Status transition validation
# ─────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    "todo":        {"in_progress", "archived"},
    "in_progress": {"done", "todo", "archived"},
    "done":        {"archived"},
    "archived":    set(),
}


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """Return True if moving from current_status → new_status is allowed."""
    allowed = VALID_TRANSITIONS.get(current_status, set())
    return new_status in allowed


def get_allowed_transitions(current_status: str) -> list[str]:
    """Return list of statuses reachable from current_status."""
    return sorted(VALID_TRANSITIONS.get(current_status, set()))


# ─────────────────────────────────────────────
# Summary generation
# ─────────────────────────────────────────────

def generate_task_summary(tasks: list[dict]) -> dict:
    """Produce a count summary dict from a list of task dicts."""
    summary = {
        "total":       len(tasks),
        "by_status":   {},
        "by_priority": {},
        "overdue":     0,
    }
    for task in tasks:
        s = task.get("status", "unknown")
        p = task.get("priority", "unknown")
        summary["by_status"][s]   = summary["by_status"].get(s, 0) + 1
        summary["by_priority"][p] = summary["by_priority"].get(p, 0) + 1
        if is_overdue(task.get("due_date", "")):
            summary["overdue"] += 1
    return summary
