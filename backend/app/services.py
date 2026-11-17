"""Reglas de negocio puras (sin base de datos), probadas con pruebas unitarias."""

from collections.abc import Iterable
from datetime import date

PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "done")
MAX_TITLE_LENGTH = 120
MAX_PROJECT_NAME_LENGTH = 60


def normalize_title(title: str) -> str:
    """Quita espacios sobrantes y valida que el título no quede vacío ni sea largo."""
    cleaned = " ".join(title.split())
    if not cleaned:
        raise ValueError("El título no puede estar vacío")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValueError(f"El título no puede superar {MAX_TITLE_LENGTH} caracteres")
    return cleaned


def normalize_project_name(name: str) -> str:
    """Normaliza el nombre de un proyecto: sin espacios sobrantes y no vacío."""
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("El nombre del proyecto no puede estar vacío")
    if len(cleaned) > MAX_PROJECT_NAME_LENGTH:
        raise ValueError(
            f"El nombre no puede superar {MAX_PROJECT_NAME_LENGTH} caracteres"
        )
    return cleaned


def is_overdue(due_date: date | None, status: str, today: date) -> bool:
    """Una tarea está vencida si sigue pendiente y su fecha límite ya pasó."""
    return status == "pending" and due_date is not None and due_date < today


def compute_stats(tasks: Iterable[tuple[str, date | None]], today: date) -> dict:
    """Calcula los indicadores del tablero a partir de (status, due_date)."""
    total = pending = done = overdue = 0
    for status, due_date in tasks:
        total += 1
        if status == "done":
            done += 1
        else:
            pending += 1
        if is_overdue(due_date, status, today):
            overdue += 1
    completion_rate = round(done * 100 / total, 1) if total else 0.0
    return {
        "total": total,
        "pending": pending,
        "done": done,
        "overdue": overdue,
        "completion_rate": completion_rate,
    }


def priority_rank(priority: str) -> int:
    """Orden de prioridad para listar primero lo más importante (high=0)."""
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)
