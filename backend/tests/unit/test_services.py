"""Pruebas unitarias de las reglas de negocio (sin base de datos ni HTTP)."""

from datetime import date

import pytest

from app import config
from app.services import (
    MAX_TITLE_LENGTH,
    compute_stats,
    is_overdue,
    normalize_title,
    priority_rank,
)

TODAY = date(2026, 11, 16)


class TestNormalizeTitle:
    def test_quita_espacios_sobrantes(self):
        assert normalize_title("  Comprar   leche  ") == "Comprar leche"

    def test_titulo_vacio_falla(self):
        with pytest.raises(ValueError, match="vacío"):
            normalize_title("    ")

    def test_titulo_en_el_limite_es_valido(self):
        assert len(normalize_title("a" * MAX_TITLE_LENGTH)) == MAX_TITLE_LENGTH

    def test_titulo_muy_largo_falla(self):
        with pytest.raises(ValueError, match="superar"):
            normalize_title("a" * (MAX_TITLE_LENGTH + 1))


class TestIsOverdue:
    @pytest.mark.parametrize(
        ("due", "status", "expected"),
        [
            (date(2026, 11, 15), "pending", True),  # ayer y pendiente
            (date(2026, 11, 16), "pending", False),  # vence hoy: aún no
            (date(2026, 11, 17), "pending", False),  # futura
            (date(2026, 11, 1), "done", False),  # completada nunca vence
            (None, "pending", False),  # sin fecha límite
        ],
    )
    def test_casos(self, due, status, expected):
        assert is_overdue(due, status, TODAY) is expected


class TestComputeStats:
    def test_sin_tareas(self):
        assert compute_stats([], TODAY) == {
            "total": 0,
            "pending": 0,
            "done": 0,
            "overdue": 0,
            "completion_rate": 0.0,
        }

    def test_mezcla_de_tareas(self):
        tasks = [
            ("done", None),
            ("pending", date(2026, 11, 1)),  # vencida
            ("pending", None),
        ]
        stats = compute_stats(tasks, TODAY)
        assert stats["total"] == 3
        assert stats["done"] == 1
        assert stats["pending"] == 2
        assert stats["overdue"] == 1
        assert stats["completion_rate"] == 33.3


class TestPriorityRank:
    def test_orden(self):
        assert priority_rank("high") < priority_rank("medium") < priority_rank("low")

    def test_desconocida_va_al_final(self):
        assert priority_rank("otra") == 3


class TestConfig:
    def test_database_url_explicita(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite://")
        assert config.get_database_url() == "sqlite://"

    def test_database_url_por_partes_escapa_password(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("DB_HOST", "db.example")
        monkeypatch.setenv("DB_USER", "app")
        monkeypatch.setenv("DB_PASSWORD", "p@ss/word")
        monkeypatch.setenv("DB_NAME", "tareas")
        url = config.get_database_url()
        assert url == "postgresql+psycopg://app:p%40ss%2Fword@db.example:5432/tareas"

    def test_version_y_ambiente_por_defecto(self, monkeypatch):
        monkeypatch.delenv("APP_VERSION", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        assert config.get_app_version() == "local"
        assert config.get_environment() == "local"
