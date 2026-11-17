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
const projectForm = document.getElementById("project-form");
const projectList = document.getElementById("project-list");
const projectSelect = document.getElementById("project");
const projectFilter = document.getElementById("filter-project");
let projectNames = {};

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
  const project = task.project_id ? " · " + (projectNames[task.project_id] || "") : "";
  meta.textContent =
    "Prioridad " + PRIORITY_LABELS[task.priority] + project + due + late;
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

function fillProjectSelect(select, projects, firstLabel) {
  const current = select.value;
  const first = document.createElement("option");
  first.value = "";
  first.textContent = firstLabel;
  const options = projects.map((p) => {
    const option = document.createElement("option");
    option.value = String(p.id);
    option.textContent = p.name;
    return option;
  });
  select.replaceChildren(first, ...options);
  select.value = projects.some((p) => String(p.id) === current) ? current : "";
}

function buildProjectChip(project) {
  const li = document.createElement("li");
  li.className = "project-chip";
  li.dataset.id = project.id;
  const name = document.createElement("span");
  name.className = "project-name";
  name.textContent = project.name + " (" + project.task_count + ")";
  const del = document.createElement("button");
  del.className = "project-delete-btn";
  del.type = "button";
  del.title = "Eliminar proyecto";
  del.textContent = "✕";
  del.addEventListener("click", () => deleteProject(project.id));
  li.append(name, del);
  return li;
}

async function loadProjects() {
  const projects = await request("/projects");
  projectNames = Object.fromEntries(projects.map((p) => [p.id, p.name]));
  projectList.replaceChildren(...projects.map(buildProjectChip));
  fillProjectSelect(projectSelect, projects, "Sin proyecto");
  fillProjectSelect(projectFilter, projects, "Todos los proyectos");
}

async function deleteProject(id) {
  try {
    await request("/projects/" + id, { method: "DELETE" });
    await refresh();
    showMessage("Proyecto eliminado", false);
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function loadStats() {
  const projectQuery = projectFilter.value ? "?project_id=" + projectFilter.value : "";
  const s = await request("/tasks/stats" + projectQuery);
  document.getElementById("stat-total").textContent = s.total;
  document.getElementById("stat-pending").textContent = s.pending;
  document.getElementById("stat-done").textContent = s.done;
  document.getElementById("stat-overdue").textContent = s.overdue;
  document.getElementById("stat-rate").textContent = s.completion_rate + "%";
}

async function loadTasks() {
  const params = new URLSearchParams();
  if (filter.value) params.set("status", filter.value);
  if (projectFilter.value) params.set("project_id", projectFilter.value);
  const query = params.toString() ? "?" + params.toString() : "";
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
    await refresh();
    showMessage("Tarea eliminada", false);
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
    project_id: data.get("project_id") ? Number(data.get("project_id")) : null,
  };
  try {
    await request("/tasks", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    await refresh();
    showMessage("Tarea creada", false);
  } catch (err) {
    showMessage(err.message, true);
  }
});

async function refresh() {
  await loadProjects();
  await loadTasks();
}

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.getElementById("project-name").value;
  try {
    await request("/projects", { method: "POST", body: JSON.stringify({ name }) });
    projectForm.reset();
    await refresh();
    showMessage("Proyecto creado", false);
  } catch (err) {
    showMessage(err.message, true);
  }
});

filter.addEventListener("change", loadTasks);
projectFilter.addEventListener("change", loadTasks);

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
refresh().catch((err) => showMessage(err.message, true));
