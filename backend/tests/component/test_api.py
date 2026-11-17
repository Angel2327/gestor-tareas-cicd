"""Pruebas de componente: API completa (rutas, validación y ORM) con SQLite."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture(name="client")
def fixture_client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def _create(client, **kwargs):
    payload = {"title": "Tarea de prueba", **kwargs}
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_ok(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc123")
    body = client.get("/api/health").json()
    assert body == {
        "status": "ok",
        "version": "abc123",
        "environment": "local",
        "database": "ok",
    }


def test_health_degradado_si_la_bd_falla(client):
    class BrokenSession:  # pylint: disable=too-few-public-methods
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("sin conexión"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "error"


def test_crear_y_obtener_tarea(client):
    created = _create(client, title="  Estudiar   CI/CD ", priority="high")
    assert created["title"] == "Estudiar CI/CD"
    assert created["status"] == "pending"
    assert created["priority"] == "high"

    fetched = client.get(f"/api/tasks/{created['id']}").json()
    assert fetched == created


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "x" * 121},
        {"title": "ok", "priority": "urgente"},
        {},
    ],
)
def test_crear_tarea_invalida_devuelve_422(client, payload):
    assert client.post("/api/tasks", json=payload).status_code == 422


def test_listar_ordena_por_prioridad_y_filtra(client):
    _create(client, title="baja", priority="low")
    _create(client, title="alta", priority="high")
    hecha = _create(client, title="media", priority="medium")
    client.patch(f"/api/tasks/{hecha['id']}", json={"status": "done"})

    titles = [t["title"] for t in client.get("/api/tasks").json()]
    assert titles == ["alta", "media", "baja"]

    pending = client.get("/api/tasks", params={"status": "pending"}).json()
    assert {t["title"] for t in pending} == {"alta", "baja"}

    high = client.get("/api/tasks", params={"priority": "high"}).json()
    assert [t["title"] for t in high] == ["alta"]


def test_actualizar_tarea(client):
    task = _create(client)
    response = client.patch(
        f"/api/tasks/{task['id']}", json={"status": "done", "title": "Nuevo título"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["title"] == "Nuevo título"


def test_eliminar_tarea(client):
    task = _create(client)
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_tarea_inexistente_devuelve_404(client, method):
    kwargs = {"json": {"status": "done"}} if method == "patch" else {}
    response = getattr(client, method)("/api/tasks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Tarea no encontrada"


def test_estadisticas_y_vencidas(client):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    vencida = _create(client, title="vencida", due_date=ayer)
    assert vencida["overdue"] is True
    hecha = _create(client, title="hecha")
    client.patch(f"/api/tasks/{hecha['id']}", json={"status": "done"})

    stats = client.get("/api/tasks/stats").json()
    assert stats == {
        "total": 2,
        "pending": 1,
        "done": 1,
        "overdue": 1,
        "completion_rate": 50.0,
    }


# ---------------------------------------------------------------------------
# Proyectos
# ---------------------------------------------------------------------------
def _create_project(client, name="Proyecto final", **kwargs):
    response = client.post("/api/projects", json={"name": name, **kwargs})
    assert response.status_code == 201, response.text
    return response.json()


def test_crear_y_listar_proyectos_con_conteo(client):
    final = _create_project(client, "  Proyecto   final ", description="CI/CD")
    assert final["name"] == "Proyecto final"
    assert final["task_count"] == 0
    otro = _create_project(client, "Arquitectura")
    _create(client, title="t1", project_id=final["id"])
    _create(client, title="t2", project_id=final["id"])

    projects = client.get("/api/projects").json()
    assert [p["name"] for p in projects] == ["Arquitectura", "Proyecto final"]
    counts = {p["id"]: p["task_count"] for p in projects}
    assert counts == {otro["id"]: 0, final["id"]: 2}


@pytest.mark.parametrize("payload", [{"name": "   "}, {"name": "x" * 61}, {}])
def test_crear_proyecto_invalido_devuelve_422(client, payload):
    assert client.post("/api/projects", json=payload).status_code == 422


def test_nombre_de_proyecto_duplicado_devuelve_409(client):
    _create_project(client, "Proyecto final")
    response = client.post("/api/projects", json={"name": "PROYECTO FINAL"})
    assert response.status_code == 409


def test_tarea_con_proyecto_inexistente_devuelve_422(client):
    response = client.post("/api/tasks", json={"title": "x", "project_id": 999})
    assert response.status_code == 422
    task = _create(client)
    response = client.patch(f"/api/tasks/{task['id']}", json={"project_id": 999})
    assert response.status_code == 422


def test_filtrar_tareas_y_estadisticas_por_proyecto(client):
    project = _create_project(client)
    _create(client, title="del proyecto", project_id=project["id"])
    _create(client, title="sin proyecto")

    tasks = client.get("/api/tasks", params={"project_id": project["id"]}).json()
    assert [t["title"] for t in tasks] == ["del proyecto"]
    assert tasks[0]["project_id"] == project["id"]

    stats = client.get("/api/tasks/stats", params={"project_id": project["id"]})
    assert stats.json()["total"] == 1
    assert client.get("/api/tasks/stats").json()["total"] == 2


def test_mover_tarea_a_otro_proyecto(client):
    project = _create_project(client)
    task = _create(client)
    moved = client.patch(f"/api/tasks/{task['id']}", json={"project_id": project["id"]})
    assert moved.json()["project_id"] == project["id"]


def test_eliminar_proyecto_conserva_sus_tareas(client):
    project = _create_project(client)
    task = _create(client, project_id=project["id"])

    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert client.get("/api/projects").json() == []
    assert client.get(f"/api/tasks/{task['id']}").json()["project_id"] is None


def test_eliminar_proyecto_inexistente_devuelve_404(client):
    response = client.delete("/api/projects/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Proyecto no encontrado"
