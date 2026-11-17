"""Pruebas de componente de las migraciones de Alembic (upgrade y downgrade)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(db_url: str, monkeypatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", db_url)
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def _columns(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    names = {c["name"] for c in inspect(engine).get_columns("tasks")}
    engine.dispose()
    return names


def _tables(db_url: str) -> list[str]:
    engine = create_engine(db_url)
    names = inspect(engine).get_table_names()
    engine.dispose()
    return names


def test_upgrade_crea_esquema_completo_y_downgrade_lo_revierte(tmp_path, monkeypatch):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    cfg = _alembic_config(db_url, monkeypatch)

    command.upgrade(cfg, "head")
    assert {"id", "title", "status", "priority", "due_date", "project_id"} <= _columns(
        db_url
    )
    assert "projects" in _tables(db_url)

    command.downgrade(cfg, "0002")
    assert "project_id" not in _columns(db_url)
    assert "projects" not in _tables(db_url)

    command.downgrade(cfg, "0001")
    assert "priority" not in _columns(db_url)

    command.downgrade(cfg, "base")
    assert "tasks" not in _tables(db_url)
