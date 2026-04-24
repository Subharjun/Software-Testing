"""
Integration Tests — tests/integration/test_api.py
Full HTTP-level tests against the Flask application using the test client.

Covers:
  - Authentication flows (login, JWT validation, protected routes)
  - Task CRUD: create / read / update / delete
  - Filtering and search
  - Error handling and status codes
  - Ownership isolation between users

Run:  pytest tests/integration/ -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))


# ═══════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════

class TestHealth:
    def test_health_endpoint_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_body(self, client):
        data = client.get("/health").get_json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data


# ═══════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════

class TestAuthentication:
    def test_login_valid_credentials_returns_200(self, client):
        resp = client.post("/auth/login", json={"username": "tester", "password": "tester123"})
        assert resp.status_code == 200

    def test_login_returns_token(self, client):
        resp  = client.post("/auth/login", json={"username": "tester", "password": "tester123"})
        data  = resp.get_json()
        assert "token" in data
        assert len(data["token"]) > 20

    def test_login_wrong_password_returns_401(self, client):
        resp = client.post("/auth/login", json={"username": "tester", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user_returns_401(self, client):
        resp = client.post("/auth/login", json={"username": "ghost", "password": "ghost"})
        assert resp.status_code == 401

    def test_login_missing_fields_returns_400(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 400

    def test_login_missing_password_returns_400(self, client):
        resp = client.post("/auth/login", json={"username": "tester"})
        assert resp.status_code == 400

    def test_protected_route_without_token_returns_401(self, client):
        resp = client.get("/tasks")
        assert resp.status_code == 401

    def test_protected_route_with_invalid_token_returns_401(self, client):
        resp = client.get("/tasks", headers={"Authorization": "Bearer not.a.token"})
        assert resp.status_code == 401

    def test_protected_route_with_malformed_header_returns_401(self, client):
        resp = client.get("/tasks", headers={"Authorization": "Token abc"})
        assert resp.status_code == 401

    def test_me_endpoint_returns_user_info(self, client, auth_headers):
        data = client.get("/auth/me", headers=auth_headers).get_json()
        assert "username" in data
        assert data["username"] == "tester"


# ═══════════════════════════════════════════════
# Task Creation
# ═══════════════════════════════════════════════

class TestTaskCreation:
    def test_create_task_returns_201(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "Test Task"}, headers=auth_headers)
        assert resp.status_code == 201

    def test_create_task_returns_task_data(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "My Task"}, headers=auth_headers)
        data = resp.get_json()
        assert data["title"] == "My Task"
        assert "id" in data
        assert data["status"] == "todo"
        assert data["priority"] == "medium"

    def test_create_task_with_all_fields(self, client, auth_headers):
        payload = {
            "title": "Full Task",
            "description": "A detailed description",
            "status": "in_progress",
            "priority": "high",
            "due_date": "2025-12-31",
            "tags": "backend,qa",
        }
        resp = client.post("/tasks", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["priority"] == "high"
        assert data["due_date"] == "2025-12-31"

    def test_create_task_without_title_returns_422(self, client, auth_headers):
        resp = client.post("/tasks", json={"description": "No title"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_task_invalid_status_returns_422(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "T", "status": "pending"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_task_invalid_priority_returns_422(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "T", "priority": "urgent"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_task_invalid_date_returns_422(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "T", "due_date": "31/12/2025"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_task_title_too_long_returns_422(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "x" * 121}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_task_unauthenticated_returns_401(self, client):
        resp = client.post("/tasks", json={"title": "Sneaky Task"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════
# Task Retrieval
# ═══════════════════════════════════════════════

class TestTaskRetrieval:
    @pytest.fixture(autouse=True)
    def seed_tasks(self, client, auth_headers):
        """Create a known set of tasks before each test in this class."""
        client.post("/tasks", json={"title": "Alpha Task", "priority": "high",   "status": "todo"},        headers=auth_headers)
        client.post("/tasks", json={"title": "Beta Task",  "priority": "low",    "status": "done"},        headers=auth_headers)
        client.post("/tasks", json={"title": "Gamma Task", "priority": "medium", "status": "in_progress"}, headers=auth_headers)

    def test_list_tasks_returns_200(self, client, auth_headers):
        resp = client.get("/tasks", headers=auth_headers)
        assert resp.status_code == 200

    def test_list_tasks_returns_count(self, client, auth_headers):
        data = client.get("/tasks", headers=auth_headers).get_json()
        assert "count" in data
        assert data["count"] >= 3

    def test_filter_by_status(self, client, auth_headers):
        data = client.get("/tasks?status=done", headers=auth_headers).get_json()
        statuses = [t["status"] for t in data["tasks"]]
        assert all(s == "done" for s in statuses)

    def test_filter_by_priority(self, client, auth_headers):
        data = client.get("/tasks?priority=high", headers=auth_headers).get_json()
        priorities = [t["priority"] for t in data["tasks"]]
        assert all(p == "high" for p in priorities)

    def test_search_by_title(self, client, auth_headers):
        data = client.get("/tasks?q=Alpha", headers=auth_headers).get_json()
        titles = [t["title"] for t in data["tasks"]]
        assert any("Alpha" in title for title in titles)

    def test_get_task_by_id_returns_200(self, client, auth_headers):
        created = client.post("/tasks", json={"title": "Fetch Me"}, headers=auth_headers).get_json()
        resp    = client.get(f"/tasks/{created['id']}", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_nonexistent_task_returns_404(self, client, auth_headers):
        resp = client.get("/tasks/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_task_stats_returns_200(self, client, auth_headers):
        resp = client.get("/tasks/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert "stats" in resp.get_json()


# ═══════════════════════════════════════════════
# Task Updates
# ═══════════════════════════════════════════════

class TestTaskUpdate:
    @pytest.fixture
    def task_id(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "Update Target"}, headers=auth_headers)
        return resp.get_json()["id"]

    def test_update_title_returns_200(self, client, auth_headers, task_id):
        resp = client.put(f"/tasks/{task_id}", json={"title": "Updated Title"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_update_title_reflects_in_response(self, client, auth_headers, task_id):
        client.put(f"/tasks/{task_id}", json={"title": "New Name"}, headers=auth_headers)
        data = client.get(f"/tasks/{task_id}", headers=auth_headers).get_json()
        assert data["title"] == "New Name"

    def test_update_status_valid(self, client, auth_headers, task_id):
        resp = client.put(f"/tasks/{task_id}", json={"status": "in_progress"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "in_progress"

    def test_update_invalid_status_returns_422(self, client, auth_headers, task_id):
        resp = client.put(f"/tasks/{task_id}", json={"status": "flying"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_empty_body_returns_400(self, client, auth_headers, task_id):
        resp = client.put(f"/tasks/{task_id}", json={}, headers=auth_headers)
        assert resp.status_code == 400

    def test_update_nonexistent_task_returns_404(self, client, auth_headers):
        resp = client.put("/tasks/999999", json={"title": "Ghost"}, headers=auth_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════
# Task Deletion
# ═══════════════════════════════════════════════

class TestTaskDeletion:
    @pytest.fixture
    def task_id(self, client, auth_headers):
        resp = client.post("/tasks", json={"title": "Delete Target"}, headers=auth_headers)
        return resp.get_json()["id"]

    def test_delete_task_returns_200(self, client, auth_headers, task_id):
        resp = client.delete(f"/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_task_removes_from_list(self, client, auth_headers, task_id):
        client.delete(f"/tasks/{task_id}", headers=auth_headers)
        resp = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_task_returns_404(self, client, auth_headers):
        resp = client.delete("/tasks/999999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_unauthenticated_returns_401(self, client, task_id):
        resp = client.delete(f"/tasks/{task_id}")
        assert resp.status_code == 401
