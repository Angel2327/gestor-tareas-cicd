"""Configuración común: las pruebas usan SQLite en memoria, no PostgreSQL."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
