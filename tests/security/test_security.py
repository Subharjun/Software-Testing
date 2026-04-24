"""
Security Tests — tests/security/test_security.py
OWASP-inspired security checks against the Task Manager API.

Tests:
  - SQL Injection prevention
  - XSS payload handling
  - Authentication bypass attempts
  - Sensitive data exposure
  - Mass assignment / parameter pollution
  - Rate-limit-adjacent: over-large payloads

Run:  pytest tests/security/ -v
"""

import pytest


# ═══════════════════════════════════════════════
# SQL Injection
# ═══════════════════════════════════════════════

class TestSQLInjection:
    """
    These payloads attempt classic SQL injection.  The API should either
    reject the payload (422) or handle it safely without leaking data (200/201
    with sanitised output). A 500 server error is a FAIL.
    """

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE tasks; --",
        "1; SELECT * FROM users; --",
        "' UNION SELECT username, password FROM users --",
        "admin'--",
        "\" OR \"\"=\"",
        "' OR 1=1--",
        "1' AND 1=1 UNION SELECT null, username, password FROM users--",
    ]

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_in_title_does_not_crash(self, client, auth_headers, payload):
        resp = client.post("/tasks", json={"title": payload}, headers=auth_headers)
        assert resp.status_code in (201, 422), (
            f"SQL injection in title returned {resp.status_code}; expected 201 or 422"
        )

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_in_search_does_not_crash(self, client, auth_headers, payload):
        resp = client.get(f"/tasks?q={payload}", headers=auth_headers)
        assert resp.status_code in (200, 400), (
            f"SQL injection in search param returned {resp.status_code}"
        )

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_sql_injection_in_login_does_not_bypass_auth(self, client, payload):
        resp = client.post("/auth/login", json={"username": payload, "password": payload})
        # Must NOT return 200 (would mean bypass)
        assert resp.status_code != 200, (
            f"SQL injection login bypass with payload: {payload!r}"
        )


# ═══════════════════════════════════════════════
# XSS Prevention
# ═══════════════════════════════════════════════

class TestXSSPrevention:
    """
    API returns JSON, so XSS in stored data is mitigated at the browser layer.
    We verify the raw script tags are stored/returned verbatim (not executed
    server-side) and that the response Content-Type is strictly application/json.
    """

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "';alert('xss');//",
        "\"><script>document.cookie</script>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_title_response_is_json(self, client, auth_headers, payload):
        resp = client.post("/tasks", json={"title": payload}, headers=auth_headers)
        assert "application/json" in resp.content_type, (
            "Response is not JSON — potential raw HTML execution risk"
        )

    def test_xss_stored_and_retrieved_verbatim(self, client, auth_headers):
        """The payload is stored as text, not executed."""
        xss = "<script>alert('hack')</script>"
        created = client.post("/tasks", json={"title": xss}, headers=auth_headers).get_json()
        fetched  = client.get(f"/tasks/{created['id']}", headers=auth_headers).get_json()
        # Title must be stored, not evaluated/stripped at API level
        assert fetched["title"] == xss


# ═══════════════════════════════════════════════
# Authentication Bypass
# ═══════════════════════════════════════════════

class TestAuthenticationBypass:
    def test_no_token_blocked(self, client):
        for method, url in [
            ("GET",    "/tasks"),
            ("POST",   "/tasks"),
            ("GET",    "/tasks/1"),
            ("PUT",    "/tasks/1"),
            ("DELETE", "/tasks/1"),
            ("GET",    "/tasks/stats"),
        ]:
            resp = getattr(client, method.lower())(url)
            assert resp.status_code == 401, f"{method} {url} should require auth"

    def test_tampered_signature_rejected(self, client, auth_token):
        # Replace the signature segment (3rd part of JWT) with garbage
        parts = auth_token.split(".")
        assert len(parts) == 3, "Token must have 3 JWT segments"
        bad_token = parts[0] + "." + parts[1] + ".invalidsignatureXXXXXXXXX"
        resp = client.get("/tasks", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401, (
            f"Tampered JWT signature was accepted (returned {resp.status_code})"
        )

    def test_none_algorithm_attack_rejected(self, client):
        """JWT 'none' algorithm exploit: crafted token with no signature."""
        import base64
        header  = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'{"user_id":1,"username":"admin"}').rstrip(b"=").decode()
        fake_token = f"{header}.{payload}."
        resp = client.get("/tasks", headers={"Authorization": f"Bearer {fake_token}"})
        assert resp.status_code == 401, "None-algorithm JWT should be rejected"

    def test_empty_bearer_token_rejected(self, client):
        resp = client.get("/tasks", headers={"Authorization": "Bearer "})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════
# Sensitive Data Exposure
# ═══════════════════════════════════════════════

class TestSensitiveDataExposure:
    def test_login_response_does_not_expose_password(self, client):
        data = client.post(
            "/auth/login",
            json={"username": "tester", "password": "tester123"}
        ).get_json()
        assert "password" not in data

    def test_task_response_does_not_include_other_users_data(self, client, auth_headers):
        """Tester's task list must not expose admin's tasks."""
        # Log in as admin and create a task
        admin_token = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        ).get_json()["token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        client.post("/tasks", json={"title": "Admin Secret Task"}, headers=admin_headers)

        # Tester's list should not contain admin's task
        my_tasks = client.get("/tasks", headers=auth_headers).get_json()["tasks"]
        titles   = [t["title"] for t in my_tasks]
        assert "Admin Secret Task" not in titles


# ═══════════════════════════════════════════════
# Oversized Payload (DoS Prevention)
# ═══════════════════════════════════════════════

class TestOversizedPayloads:
    def test_extremely_large_title_rejected(self, client, auth_headers):
        resp = client.post(
            "/tasks",
            json={"title": "A" * 10_000},
            headers=auth_headers
        )
        # Must be rejected (422) or at worst a 4xx — never a 500
        assert resp.status_code in range(400, 500), (
            f"Oversized title returned {resp.status_code}"
        )

    def test_extremely_large_description_rejected(self, client, auth_headers):
        resp = client.post(
            "/tasks",
            json={"title": "Normal", "description": "B" * 50_000},
            headers=auth_headers
        )
        assert resp.status_code in range(400, 500)
