"use strict";

// El frontend llama a la API por ruta relativa (/api). En AWS el ALB enruta
// /api/* al backend; en local, Nginx hace de proxy hacia el contenedor backend.
const API = "/api";
const PRIORITY_LABELS = { low: "Baja", medium: "Media", high: "Alta" };

const form = document.getElementById("task-form");
const list = document.getElementById("task-list");
const message = document.getElementById("message");
const filter = document.getElementById("filter-status");
const emptyMsg = document.getElementById("empty-msg");

function showMessage(text, isError) {
  message.textContent = text;
  message.className = isError ? "error" : "ok";
}

async function request(path, options) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail[0].msg : body.detail;
    throw new Error(detail || "Error " + response.status);
  }
  return response.status === 204 ? null : response.json();
}

function buildTaskItem(task) {
  // Se usa textContent (no innerHTML) para evitar XSS con el texto del usuario.
  const li = document.createElement("li");
  li.className = "task " + task.status + (task.overdue ? " overdue" : "");
  li.dataset.id = task.id;

  const info = document.createElement("div");
  const title = document.createElement("span");
  title.className = "task-title";
  title.textContent = task.title;
  const meta = document.createElement("small");
  meta.className = "task-meta";
  const due = task.due_date ? " · vence " + task.due_date : "";
  const late = task.overdue ? " · VENCIDA" : "";
  meta.textContent = "Prioridad " + PRIORITY_LABELS[task.priority] + due + late;
  info.append(title, document.createElement("br"), meta);
  if (task.description) {
    const desc = document.createElement("p");
    desc.className = "task-desc";
    desc.textContent = task.description;
    info.append(desc);
  }

  const actions = document.createElement("div");
  actions.className = "actions";
  const toggle = document.createElement("button");
  toggle.className = "toggle-btn";
  toggle.textContent = task.status === "done" ? "Reabrir" : "Completar";
  toggle.addEventListener("click", () =>
    updateTask(task.id, { status: task.status === "done" ? "pending" : "done" })
  );
  const del = document.createElement("button");
  del.className = "delete-btn";
  del.textContent = "Eliminar";
  del.addEventListener("click", () => deleteTask(task.id));
  actions.append(toggle, del);

  li.append(info, actions);
  return li;
}

async function loadStats() {
  const s = await request("/tasks/stats");
  document.getElementById("stat-total").textContent = s.total;
  document.getElementById("stat-pending").textContent = s.pending;
  document.getElementById("stat-done").textContent = s.done;
  document.getElementById("stat-overdue").textContent = s.overdue;
  document.getElementById("stat-rate").textContent = s.completion_rate + "%";
}

async function loadTasks() {
  const query = filter.value ? "?status=" + filter.value : "";
  const tasks = await request("/tasks" + query);
  list.replaceChildren(...tasks.map(buildTaskItem));
  emptyMsg.hidden = tasks.length > 0;
  await loadStats();
}

async function updateTask(id, changes) {
  try {
    await request("/tasks/" + id, { method: "PATCH", body: JSON.stringify(changes) });
    await loadTasks();
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function deleteTask(id) {
  try {
    await request("/tasks/" + id, { method: "DELETE" });
    showMessage("Tarea eliminada", false);
    await loadTasks();
  } catch (err) {
    showMessage(err.message, true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const payload = {
    title: data.get("title"),
    description: data.get("description") || null,
    priority: data.get("priority"),
    due_date: data.get("due_date") || null,
  };
  try {
    await request("/tasks", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    showMessage("Tarea creada", false);
    await loadTasks();
  } catch (err) {
    showMessage(err.message, true);
  }
});

filter.addEventListener("change", loadTasks);

async function loadHealth() {
  try {
    const health = await request("/health");
    document.getElementById("app-version").textContent = health.version;
    document.getElementById("env-badge").textContent = health.environment;
  } catch (err) {
    document.getElementById("app-version").textContent = "sin conexión";
    console.error(err);
  }
}

loadHealth().catch((err) => console.error(err));
loadTasks().catch((err) => showMessage(err.message, true));
