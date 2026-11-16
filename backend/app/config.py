"""Configuración de la aplicación leída desde variables de entorno."""

import os
from urllib.parse import quote_plus


def get_database_url() -> str:
    """Devuelve la URL de conexión a la base de datos.

    Si existe DATABASE_URL se usa tal cual (local y pruebas).
    Si no, se arma con DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD (AWS).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "tareas")
    user = os.getenv("DB_USER", "tareas")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def get_app_version() -> str:
    """Versión desplegada (SHA del commit). 'local' si no se definió."""
    return os.getenv("APP_VERSION", "local")


def get_environment() -> str:
    """Nombre del ambiente: local, staging o production."""
    return os.getenv("ENVIRONMENT", "local")
