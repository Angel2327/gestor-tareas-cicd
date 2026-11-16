"""Operaciones sobre la base de datos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate
from app.services import priority_rank


def list_tasks(
    db: Session, status: str | None = None, priority: str | None = None
) -> list[Task]:
    """Lista tareas filtradas, primero las de mayor prioridad y luego las más nuevas."""
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    tasks = list(db.scalars(query.order_by(Task.id.desc())))
    return sorted(tasks, key=lambda t: priority_rank(t.priority))


def get_task(db: Session, task_id: int) -> Task | None:
    """Busca una tarea por id."""
    return db.get(Task, task_id)


def create_task(db: Session, data: TaskCreate) -> Task:
    """Crea una tarea pendiente."""
    task = Task(**data.model_dump(), status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task: Task, data: TaskUpdate) -> Task:
    """Actualiza solo los campos enviados."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    """Elimina una tarea."""
    db.delete(task)
    db.commit()
