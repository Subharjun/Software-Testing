/* ═══════════════════════════════════════════════════════════
   QA Forge — Frontend JavaScript
   Handles auth, task CRUD, filtering, and stats
   ═══════════════════════════════════════════════════════════ */

const API = "http://localhost:5050";

/* ─── State ───────────────────────────────────────────────── */
let token       = localStorage.getItem("qa_token") || null;
let editingId   = null;
let allTasks    = [];
let searchTimer = null;

/* ─── DOM refs ────────────────────────────────────────────── */
const loginSection  = document.getElementById("login-section");
const dashboard     = document.getElementById("dashboard");
const authError     = document.getElementById("auth-error");
const navUsername   = document.getElementById("nav-username");

const taskList      = document.getElementById("task-list");
const searchInput   = document.getElementById("search-input");
const statusFilter  = document.getElementById("status-filter");
const priorityFilter= document.getElementById("priority-filter");

const taskModal     = document.getElementById("task-modal");
const modalTitle    = document.getElementById("modal-title");
const modalError    = document.getElementById("modal-error");
const titleInput    = document.getElementById("task-title-input");
const descInput     = document.getElementById("task-desc-input");
const statusInput   = document.getElementById("task-status-input");
const priorityInput = document.getElementById("task-priority-input");
const dueInput      = document.getElementById("task-due-input");
const tagsInput     = document.getElementById("task-tags-input");

/* ─── Helpers ─────────────────────────────────────────────── */
const headers = (extra = {}) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
  ...extra,
});

function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError(el) {
  el.textContent = "";
  el.classList.add("hidden");
}

async function apiFetch(path, opts = {}) {
  const resp = await fetch(`${API}${path}`, { ...opts, headers: headers() });
  const data = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, data };
}

function formatDate(str) {
  if (!str) return "";
  const d = new Date(str + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function isOverdue(due) {
  if (!due) return false;
  return new Date(due) < new Date(new Date().toDateString());
}

/* ─── Auth ────────────────────────────────────────────────── */
document.getElementById("login-btn").addEventListener("click", async () => {
  hideError(authError);
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  if (!username || !password) { showError(authError, "Username and password are required."); return; }

  const resp = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await resp.json();

  if (!resp.ok) {
    showError(authError, data.error || "Login failed. Please check your credentials.");
    return;
  }

  token = data.token;
  localStorage.setItem("qa_token", token);
  navUsername.textContent = `👤 ${data.username}`;
  switchToDashboard();
});

document.getElementById("password").addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("login-btn").click();
});

document.getElementById("logout-btn").addEventListener("click", () => {
  token = null;
  localStorage.removeItem("qa_token");
  switchToLogin();
});

function switchToDashboard() {
  loginSection.classList.add("hidden");
  dashboard.classList.remove("hidden");
  loadTasks();
}

function switchToLogin() {
  dashboard.classList.add("hidden");
  loginSection.classList.remove("hidden");
}

/* ─── Auto-login if token present ────────────────────────── */
(async function init() {
  if (!token) return;
  const { ok, data } = await apiFetch("/auth/me");
  if (ok) {
    navUsername.textContent = `👤 ${data.username}`;
    switchToDashboard();
  } else {
    token = null;
    localStorage.removeItem("qa_token");
  }
})();

/* ─── Task loading & rendering ────────────────────────────── */
async function loadTasks() {
  taskList.innerHTML = '<div class="loading-spinner">Loading tasks…</div>';

  const status   = statusFilter.value;
  const priority = priorityFilter.value;
  const q        = searchInput.value.trim();

  let url = "/tasks?";
  if (status)   url += `status=${status}&`;
  if (priority) url += `priority=${priority}&`;
  if (q)        url += `q=${encodeURIComponent(q)}&`;

  const { ok, data } = await apiFetch(url);
  if (!ok) { taskList.innerHTML = '<p class="empty-state"><h3>⚠️ Failed to load tasks</h3></p>'; return; }

  allTasks = data.tasks || [];
  renderTasks(allTasks);
  updateStats(allTasks);
}

function renderTasks(tasks) {
  if (!tasks.length) {
    taskList.innerHTML = `
      <div class="empty-state">
        <h3>🗒️ No tasks found</h3>
        <p>Click "New Task" to create your first task, or adjust your filters.</p>
      </div>`;
    return;
  }

  taskList.innerHTML = tasks.map(t => `
    <div class="task-card" data-id="${t.id}" data-priority="${t.priority}">
      <div class="task-card-header">
        <span class="task-title">${escHtml(t.title)}</span>
        <div class="task-actions">
          <button class="btn btn-ghost btn-icon edit-btn" data-id="${t.id}" title="Edit task" aria-label="Edit task">✏️</button>
          <button class="btn btn-danger btn-icon delete-btn" data-id="${t.id}" title="Delete task" aria-label="Delete task">🗑</button>
        </div>
      </div>
      ${t.description ? `<p class="task-description">${escHtml(t.description)}</p>` : ""}
      <div class="task-meta">
        <span class="badge status-badge" data-status="${t.status}">${fmtStatus(t.status)}</span>
        <span class="badge priority-badge" data-priority="${t.priority}">${capitalize(t.priority)}</span>
        ${t.due_date ? `<span class="task-due ${isOverdue(t.due_date) ? "overdue" : ""}">📅 ${formatDate(t.due_date)}${isOverdue(t.due_date) ? " ⚠" : ""}</span>` : ""}
      </div>
      ${t.tags ? `<div class="task-tags">${parseTags(t.tags).map(tag => `<span class="tag-chip">${escHtml(tag)}</span>`).join("")}</div>` : ""}
    </div>
  `).join("");

  // Bind actions
  document.querySelectorAll(".edit-btn").forEach(btn =>
    btn.addEventListener("click", () => openEditModal(parseInt(btn.dataset.id)))
  );
  document.querySelectorAll(".delete-btn").forEach(btn =>
    btn.addEventListener("click", () => deleteTask(parseInt(btn.dataset.id)))
  );
}

function updateStats(tasks) {
  const counts = { todo: 0, in_progress: 0, done: 0 };
  tasks.forEach(t => { if (counts[t.status] !== undefined) counts[t.status]++; });
  document.querySelector("#stat-total .stat-number").textContent  = tasks.length;
  document.querySelector("#stat-todo .stat-number").textContent   = counts.todo;
  document.querySelector("#stat-progress .stat-number").textContent = counts.in_progress;
  document.querySelector("#stat-done .stat-number").textContent   = counts.done;
}

/* ─── Filtering ───────────────────────────────────────────── */
statusFilter.addEventListener("change", loadTasks);
priorityFilter.addEventListener("change", loadTasks);
searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadTasks, 350);
});

/* ─── Modal ───────────────────────────────────────────────── */
document.getElementById("add-task-btn").addEventListener("click", openCreateModal);
document.getElementById("close-modal-btn").addEventListener("click", closeModal);
document.getElementById("cancel-task-btn").addEventListener("click", closeModal);
document.getElementById("save-task-btn").addEventListener("click", saveTask);

function openCreateModal() {
  editingId = null;
  modalTitle.textContent = "New Task";
  titleInput.value = descInput.value = dueInput.value = tagsInput.value = "";
  statusInput.value   = "todo";
  priorityInput.value = "medium";
  hideError(modalError);
  taskModal.classList.remove("hidden");
  titleInput.focus();
}

function openEditModal(id) {
  const task = allTasks.find(t => t.id === id);
  if (!task) return;
  editingId = id;
  modalTitle.textContent  = "Edit Task";
  titleInput.value        = task.title;
  descInput.value         = task.description || "";
  statusInput.value       = task.status;
  priorityInput.value     = task.priority;
  dueInput.value          = task.due_date || "";
  tagsInput.value         = task.tags || "";
  hideError(modalError);
  taskModal.classList.remove("hidden");
  titleInput.focus();
}

function closeModal() {
  taskModal.classList.add("hidden");
  editingId = null;
}

async function saveTask() {
  hideError(modalError);
  const title = titleInput.value.trim();
  if (!title) { showError(modalError, "Title is required."); return; }

  const payload = {
    title,
    description: descInput.value.trim(),
    status:      statusInput.value,
    priority:    priorityInput.value,
    due_date:    dueInput.value || undefined,
    tags:        tagsInput.value.trim(),
  };

  const { ok, data } = editingId
    ? await apiFetch(`/tasks/${editingId}`, { method: "PUT",  body: JSON.stringify(payload) })
    : await apiFetch("/tasks",              { method: "POST", body: JSON.stringify(payload) });

  if (!ok) {
    const msg = data.errors ? data.errors.join("; ") : (data.error || "Failed to save task.");
    showError(modalError, msg);
    return;
  }

  closeModal();
  loadTasks();
}

async function deleteTask(id) {
  if (!confirm("Delete this task? This cannot be undone.")) return;
  const { ok } = await apiFetch(`/tasks/${id}`, { method: "DELETE" });
  if (ok) loadTasks();
}

/* ─── Utility ─────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtStatus(s) {
  return { todo: "To Do", in_progress: "In Progress", done: "Done", archived: "Archived" }[s] || s;
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function parseTags(str) {
  return str ? str.split(",").map(t => t.trim()).filter(Boolean) : [];
}

// Close modal on overlay click
taskModal.addEventListener("click", e => { if (e.target === taskModal) closeModal(); });
