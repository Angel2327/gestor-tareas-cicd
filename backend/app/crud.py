"""Operaciones sobre la base de datos."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Project, Task
from app.schemas import ProjectCreate, TaskCreate, TaskUpdate
from app.services import priority_rank


def list_tasks(
    db: Session,
    status: str | None = None,
    priority: str | None = None,
    project_id: int | None = None,
) -> list[Task]:
    """Lista tareas filtradas, primero las de mayor prioridad y luego las más nuevas."""
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
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


def list_projects(db: Session) -> list[tuple[Project, int]]:
    """Lista los proyectos por nombre, cada uno con su cantidad de tareas."""
    query = (
        select(Project, func.count(Task.id))
        .outerjoin(Task, Task.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.name)
    )
    return list(db.execute(query).all())


def get_project(db: Session, project_id: int) -> Project | None:
    """Busca un proyecto por id."""
    return db.get(Project, project_id)


def get_project_by_name(db: Session, name: str) -> Project | None:
    """Busca un proyecto por nombre (sin distinguir mayúsculas)."""
    query = select(Project).where(func.lower(Project.name) == name.lower())
    return db.scalars(query).first()


def create_project(db: Session, data: ProjectCreate) -> Project:
    """Crea un proyecto."""
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    """Elimina un proyecto; sus tareas se conservan sin proyecto."""
    db.execute(
        update(Task).where(Task.project_id == project.id).values(project_id=None)
    )
    db.delete(project)
    db.commit()
