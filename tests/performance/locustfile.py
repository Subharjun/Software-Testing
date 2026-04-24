"""
Performance / Load Tests — tests/performance/locustfile.py
Simulates realistic user load on the Task Manager API using Locust.

Usage:
  # Headless: 50 users, spawn 5/sec, run for 60s
  locust -f tests/performance/locustfile.py \
         --headless -u 50 -r 5 -t 60s \
         --host http://localhost:5050 \
         --html reports/performance_report.html

  # Interactive web UI:
  locust -f tests/performance/locustfile.py --host http://localhost:5050
"""

import random
from locust import HttpUser, task, between, events


USERS = [
    {"username": "tester", "password": "tester123"},
    {"username": "admin",  "password": "admin123"},
]

PRIORITIES = ["low", "medium", "high", "critical"]
STATUSES   = ["todo", "in_progress", "done"]

SAMPLE_TITLES = [
    "Fix login bug",
    "Write API documentation",
    "Deploy to staging",
    "Review pull requests",
    "Set up monitoring",
    "Performance testing",
    "Database migration",
    "Write unit tests",
    "Code review",
    "Security audit",
]


class TaskManagerUser(HttpUser):
    """
    Simulates a user who logs in, performs CRUD on tasks,
    then logs out. Wait time mimics realistic think time.
    """
    wait_time = between(0.5, 2.5)
    token     = None

    def on_start(self):
        """Authenticate once at the start of each virtual user session."""
        creds = random.choice(USERS)
        resp  = self.client.post("/auth/login", json=creds, name="/auth/login")
        if resp.status_code == 200:
            self.token = resp.json().get("token")
        else:
            self.token = None

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ── Read-heavy tasks (weighted higher) ────────────────────────────────

    @task(5)
    def list_tasks(self):
        """Most common operation — listing all tasks."""
        self.client.get("/tasks", headers=self._headers(), name="GET /tasks")

    @task(3)
    def list_tasks_filtered(self):
        """Filter by status to simulate realistic query pattern."""
        status = random.choice(STATUSES)
        self.client.get(
            f"/tasks?status={status}",
            headers=self._headers(),
            name="GET /tasks?status=[status]"
        )

    @task(2)
    def search_tasks(self):
        q = random.choice(["bug", "deploy", "review", "test"])
        self.client.get(
            f"/tasks?q={q}",
            headers=self._headers(),
            name="GET /tasks?q=[search]"
        )

    # ── Write tasks (weighted lower) ──────────────────────────────────────

    @task(2)
    def create_task(self):
        payload = {
            "title":    random.choice(SAMPLE_TITLES),
            "priority": random.choice(PRIORITIES),
            "status":   "todo",
            "tags":     "load-test",
        }
        resp = self.client.post(
            "/tasks",
            json=payload,
            headers=self._headers(),
            name="POST /tasks"
        )
        if resp.status_code == 201:
            task_id = resp.json().get("id")
            if task_id:
                # Also test get-by-id
                self.client.get(
                    f"/tasks/{task_id}",
                    headers=self._headers(),
                    name="GET /tasks/[id]"
                )

    @task(1)
    def update_task(self):
        """Update a random existing task."""
        tasks_resp = self.client.get("/tasks", headers=self._headers(), name="GET /tasks (for update)")
        if tasks_resp.status_code != 200:
            return
        tasks = tasks_resp.json().get("tasks", [])
        if not tasks:
            return
        task = random.choice(tasks)
        self.client.put(
            f"/tasks/{task['id']}",
            json={"status": random.choice(STATUSES)},
            headers=self._headers(),
            name="PUT /tasks/[id]"
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="GET /health")

    @task(1)
    def get_stats(self):
        self.client.get("/tasks/stats", headers=self._headers(), name="GET /tasks/stats")


class AdminUser(HttpUser):
    """
    Administrative user performing heavier write operations.
    Lower weight — only 1 in 5 simulated users is an admin.
    """
    wait_time = between(1, 3)
    weight    = 1
    token     = None

    def on_start(self):
        resp = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"},
            name="/auth/login [admin]"
        )
        if resp.status_code == 200:
            self.token = resp.json().get("token")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def bulk_read(self):
        self.client.get("/tasks", headers=self._headers(), name="GET /tasks [admin]")

    @task(2)
    def create_and_complete_task(self):
        resp = self.client.post(
            "/tasks",
            json={"title": "Admin task", "priority": "critical"},
            headers=self._headers(),
            name="POST /tasks [admin]"
        )
        if resp.status_code == 201:
            task_id = resp.json()["id"]
            self.client.put(
                f"/tasks/{task_id}",
                json={"status": "done"},
                headers=self._headers(),
                name="PUT /tasks/[id] [admin]"
            )


# ── Custom event hooks (for reporting) ────────────────────────────────────────

@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    """Print a summary when the test ends."""
    stats = environment.stats
    print("\n" + "="*60)
    print("📊 QA Forge Performance Test Summary")
    print("="*60)
    for name, entry in stats.entries.items():
        print(f"  {name[1]:40s}  avg={entry.avg_response_time:.0f}ms  fail%={entry.fail_ratio*100:.1f}%")
    print("="*60)
