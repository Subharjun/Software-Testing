"""
QA Forge - Task Manager API
System Under Test (SUT) for comprehensive software testing demonstration.
"""

import os
import re
import jwt
import datetime
import sqlite3
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "qa-forge-dev-secret-2024")
app.config["DATABASE"] = os.environ.get("DATABASE", "qa_forge.db")

# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
    return db


def close_db(_exception=None):
    """Teardown: close the per-request DB connection."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


app.teardown_appcontext(close_db)


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            role     TEXT    NOT NULL DEFAULT 'user',
            created_at TEXT  NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT,
            status      TEXT    NOT NULL DEFAULT 'todo',
            priority    TEXT    NOT NULL DEFAULT 'medium',
            due_date    TEXT,
            tags        TEXT,
            owner_id    INTEGER NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );

        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('admin', 'admin123', 'admin');
        INSERT OR IGNORE INTO users (username, password, role)
        VALUES ('tester', 'tester123', 'user');
    """)
    db.commit()
    db.close()


init_db()

# ─────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────

VALID_STATUSES   = {"todo", "in_progress", "done", "archived"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
DATE_PATTERN     = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_task_payload(data, require_title=True):
    """Validate task fields. Returns (errors: list, cleaned: dict)."""
    errors  = []
    cleaned = {}

    title = data.get("title", "").strip()
    if require_title and not title:
        errors.append("title is required")
    elif title:
        if len(title) > 120:
            errors.append("title must be ≤ 120 characters")
        cleaned["title"] = title

    desc = data.get("description", "")
    if desc and len(desc) > 1000:
        errors.append("description must be ≤ 1000 characters")
    else:
        cleaned["description"] = desc

    status = data.get("status")
    if status is not None:
        if status not in VALID_STATUSES:
            errors.append(f"status must be one of {sorted(VALID_STATUSES)}")
        else:
            cleaned["status"] = status

    priority = data.get("priority")
    if priority is not None:
        if priority not in VALID_PRIORITIES:
            errors.append(f"priority must be one of {sorted(VALID_PRIORITIES)}")
        else:
            cleaned["priority"] = priority

    due_date = data.get("due_date")
    if due_date is not None and due_date != "":
        if not DATE_PATTERN.match(str(due_date)):
            errors.append("due_date must be in YYYY-MM-DD format")
        else:
            # Validate it's a real calendar date (e.g. reject month 13, day 32)
            try:
                datetime.datetime.strptime(due_date, "%Y-%m-%d")
                cleaned["due_date"] = due_date
            except ValueError:
                errors.append("due_date is not a valid calendar date")

    tags = data.get("tags", "")
    if tags and len(tags) > 200:
        errors.append("tags string must be ≤ 200 characters")
    else:
        cleaned["tags"] = tags

    return errors, cleaned


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            g.current_user_id = payload["user_id"]
            g.current_username = payload["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/auth/login", methods=["POST"])
def login():
    """Authenticate user and return JWT."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    db   = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id":  user["id"],
        "username": user["username"],
        "role":     user["role"],
        "exp":      now + datetime.timedelta(hours=24),
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    return jsonify({"token": token, "username": user["username"], "role": user["role"]}), 200


@app.route("/auth/me", methods=["GET"])
@token_required
def me():
    return jsonify({"user_id": g.current_user_id, "username": g.current_username}), 200


# ─────────────────────────────────────────────
# Tasks CRUD
# ─────────────────────────────────────────────

@app.route("/tasks", methods=["POST"])
@token_required
def create_task():
    data = request.get_json(silent=True) or {}
    errors, cleaned = validate_task_payload(data, require_title=True)
    if errors:
        return jsonify({"errors": errors}), 422

    db = get_db()
    cur = db.execute(
        """INSERT INTO tasks (title, description, status, priority, due_date, tags, owner_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            cleaned.get("title"),
            cleaned.get("description", ""),
            cleaned.get("status", "todo"),
            cleaned.get("priority", "medium"),
            cleaned.get("due_date"),
            cleaned.get("tags", ""),
            g.current_user_id,
        )
    )
    db.commit()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(task)), 201


@app.route("/tasks", methods=["GET"])
@token_required
def list_tasks():
    status   = request.args.get("status")
    priority = request.args.get("priority")
    search   = request.args.get("q", "")

    query  = "SELECT * FROM tasks WHERE owner_id = ?"
    params = [g.current_user_id]

    if status:
        query  += " AND status = ?"
        params.append(status)
    if priority:
        query  += " AND priority = ?"
        params.append(priority)
    if search:
        query  += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]

    query += " ORDER BY created_at DESC"

    db    = get_db()
    tasks = db.execute(query, params).fetchall()
    return jsonify({"tasks": [dict(t) for t in tasks], "count": len(tasks)}), 200


@app.route("/tasks/<int:task_id>", methods=["GET"])
@token_required
def get_task(task_id):
    db   = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
        (task_id, g.current_user_id)
    ).fetchone()
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(dict(task)), 200


@app.route("/tasks/<int:task_id>", methods=["PUT"])
@token_required
def update_task(task_id):
    db   = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
        (task_id, g.current_user_id)
    ).fetchone()
    if not task:
        return jsonify({"error": "Task not found"}), 404

    data = request.get_json(silent=True) or {}
    # Reject completely empty bodies immediately
    if not data:
        return jsonify({"error": "No fields to update"}), 400

    errors, cleaned = validate_task_payload(data, require_title=False)
    if errors:
        return jsonify({"errors": errors}), 422

    if not cleaned:
        return jsonify({"error": "No recognised fields to update"}), 400

    set_clause = ", ".join(f"{k} = ?" for k in cleaned)
    now        = datetime.datetime.now(datetime.timezone.utc).isoformat()
    values     = list(cleaned.values()) + [now, task_id]
    db.execute(
        f"UPDATE tasks SET {set_clause}, updated_at = ? WHERE id = ?",
        values
    )
    db.commit()
    updated = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(dict(updated)), 200


@app.route("/tasks/<int:task_id>", methods=["DELETE"])
@token_required
def delete_task(task_id):
    db   = get_db()
    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
        (task_id, g.current_user_id)
    ).fetchone()
    if not task:
        return jsonify({"error": "Task not found"}), 404
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"message": "Task deleted successfully"}), 200


@app.route("/tasks/stats", methods=["GET"])
@token_required
def task_stats():
    db   = get_db()
    rows = db.execute(
        """SELECT status, priority, COUNT(*) as count
           FROM tasks WHERE owner_id = ?
           GROUP BY status, priority""",
        (g.current_user_id,)
    ).fetchall()
    return jsonify({"stats": [dict(r) for r in rows]}), 200


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "QA Forge API", "version": "1.0.0"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5050)
