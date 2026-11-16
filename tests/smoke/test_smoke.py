"""Pruebas de humo (post-despliegue): rápidas y sin modificar datos.

Si alguna falla en Producción, el pipeline hace rollback automático.
"""

import requests

TIMEOUT = 10


def test_frontend_carga(base_url):
    response = requests.get(base_url + "/", timeout=TIMEOUT)
    assert response.status_code == 200
    assert "Gestor de Tareas" in response.text


def test_frontend_healthz(base_url):
    response = requests.get(base_url + "/healthz", timeout=TIMEOUT)
    assert response.status_code == 200


def test_api_health_ok_con_bd_y_version(base_url, expected_version):
    response = requests.get(base_url + "/api/health", timeout=TIMEOUT)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    if expected_version:
        assert body["version"] == expected_version


def test_api_lista_tareas(base_url):
    response = requests.get(base_url + "/api/tasks", timeout=TIMEOUT)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
