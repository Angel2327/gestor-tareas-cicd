"""Esquemas de entrada y salida de la API (Pydantic)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services import normalize_project_name, normalize_title

Priority = Literal["low", "medium", "high"]
Status = Literal["pending", "done"]


class TaskCreate(BaseModel):
    """Datos para crear una tarea."""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: Priority = "medium"
    due_date: date | None = None
    project_id: int | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        """Normaliza el título con la regla de negocio."""
        return normalize_title(value)


class TaskUpdate(BaseModel):
    """Datos para actualizar una tarea (todos opcionales)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    priority: Priority | None = None
    status: Status | None = None
    due_date: date | None = None
    project_id: int | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        """Normaliza el título si viene en la petición."""
        return normalize_title(value) if value is not None else None


class TaskOut(BaseModel):
    """Tarea devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    priority: Priority
    status: Status
    due_date: date | None
    project_id: int | None = None
    overdue: bool = False
    created_at: datetime
    updated_at: datetime


class Stats(BaseModel):
    """Indicadores del tablero."""

    total: int
    pending: int
    done: int
    overdue: int
    completion_rate: float


class ProjectCreate(BaseModel):
    """Datos para crear un proyecto."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        """Normaliza el nombre con la regla de negocio."""
        return normalize_project_name(value)


class ProjectOut(BaseModel):
    """Proyecto devuelto por la API, con su cantidad de tareas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    task_count: int = 0
    created_at: datetime
