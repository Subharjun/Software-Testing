"""
conftest.py — shared Pytest fixtures for all test levels.
"""

import os
import sys
import pytest
import tempfile

# ── Make backend importable by both pytest and Pylance ──────────────────────
_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


@pytest.fixture(scope="session")
def app():
    """Create a Flask test application backed by a temp SQLite database."""
    import app as flask_app  # type: ignore[import-not-found]  # resolved via sys.path

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    flask_app.app.config["TESTING"]  = True
    flask_app.app.config["DATABASE"] = db_path
    flask_app.init_db()

    yield flask_app.app

    os.unlink(db_path)


@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(scope="session")
def auth_token(client):
    """JWT token for the default 'tester' user."""
    resp = client.post(
        "/auth/login",
        json={"username": "tester", "password": "tester123"},
    )
    return resp.get_json()["token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
