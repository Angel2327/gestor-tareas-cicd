"""Configuración común de las pruebas que corren contra un ambiente desplegado.

APP_BASE_URL: URL del ambiente (http://localhost:8080 en CI, URL del ALB en AWS).
EXPECTED_VERSION: SHA esperado en /api/health (opcional).
"""

import os

import pytest


@pytest.fixture(scope="session", name="base_url")
def fixture_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:8080").rstrip("/")


@pytest.fixture(scope="session", name="expected_version")
def fixture_expected_version() -> str | None:
    return os.getenv("EXPECTED_VERSION")
