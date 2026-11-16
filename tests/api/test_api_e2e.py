"""Pruebas funcionales de la API de punta a punta (pre-producción).

Recorren el ciclo de vida completo de una tarea contra el ambiente real:
ALB -> backend en ECS -> PostgreSQL en RDS. Cada prueba borra lo que crea.
"""

import uuid
from datetime import date, timedelta

import pytest
import requests

TIMEOUT = 10


@pytest.fixture(name="api")
def fixture_api(base_url):
    return base_url + "/api"


@pytest.fixture(name="task")
def fixture_task(api):
    title = f"e2e-{uuid.uuid4().hex[:8]}"
    response = requests.post(
        api + "/tasks", json={"title": title, "priority": "high"}, timeout=TIMEOUT
    )
    assert response.status_code == 201, response.text
    created = response.json()
    yield created
    requests.delete(f"{api}/tasks/{created['id']}", timeout=TIMEOUT)


def test_ciclo_de_vida_completo(api, task):
    # Leer
    fetched = requests.get(f"{api}/tasks/{task['id']}", timeout=TIMEOUT).json()
    assert fetched["title"] == task["title"]
    assert fetched["status"] == "pending"

    # Actualizar (completar)
    updated = requests.patch(
        f"{api}/tasks/{task['id']}", json={"status": "done"}, timeout=TIMEOUT
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "done"

    # Aparece en el filtro de completadas
    done = requests.get(api + "/tasks", params={"status": "done"}, timeout=TIMEOUT)
    assert task["id"] in [t["id"] for t in done.json()]


def test_eliminar_tarea(api):
    created = requests.post(
        api + "/tasks", json={"title": "e2e-borrar"}, timeout=TIMEOUT
    ).json()
    assert (
        requests.delete(f"{api}/tasks/{created['id']}", timeout=TIMEOUT).status_code
        == 204
    )
    response = requests.get(f"{api}/tasks/{created['id']}", timeout=TIMEOUT)
    assert response.status_code == 404


def test_tarea_vencida_se_marca(api):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    created = requests.post(
        api + "/tasks", json={"title": "e2e-vencida", "due_date": ayer}, timeout=TIMEOUT
    ).json()
    try:
        assert created["overdue"] is True
        stats = requests.get(api + "/tasks/stats", timeout=TIMEOUT).json()
        assert stats["overdue"] >= 1
    finally:
        requests.delete(f"{api}/tasks/{created['id']}", timeout=TIMEOUT)


def test_validacion_rechaza_datos_invalidos(api):
    response = requests.post(
        api + "/tasks", json={"title": "  ", "priority": "urgente"}, timeout=TIMEOUT
    )
    assert response.status_code == 422


def test_migraciones_aplicadas(api, task):
    # Si la migración 0002 no se hubiera aplicado, priority y due_date no existirían.
    assert task["priority"] == "high"
    assert "due_date" in task
