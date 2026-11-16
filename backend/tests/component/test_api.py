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
