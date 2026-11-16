"""API REST del Gestor de Tareas (FastAPI)."""

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud
from app.config import get_app_version, get_environment
from app.database import get_db
from app.models import Task
from app.schemas import Priority, Stats, Status, TaskCreate, TaskOut, TaskUpdate
from app.services import compute_stats, is_overdue

app = FastAPI(
    title="Gestor de Tareas API",
    version=get_app_version(),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

NOT_FOUND = "Tarea no encontrada"


def _to_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.overdue = is_overdue(task.due_date, task.status, date.today())
    return out


def _get_or_404(db: Session, task_id: int) -> Task:
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return task


@app.get("/api/health")
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    """Estado de la API y de la base de datos. Lo usan el ALB y las pruebas de humo."""
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if database == "ok" else "degraded",
        "version": get_app_version(),
        "environment": get_environment(),
        "database": database,
    }


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    task_status: Status | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    """Lista las tareas, con filtros opcionales por estado y prioridad."""
    return [_to_out(t) for t in crud.list_tasks(db, task_status, priority)]


@app.get("/api/tasks/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)) -> Stats:
    """Indicadores: total, pendientes, completadas, vencidas y % de avance."""
    rows = db.execute(select(Task.status, Task.due_date)).all()
    return Stats(**compute_stats(((r[0], r[1]) for r in rows), date.today()))


@app.post("/api/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    """Crea una tarea."""
    return _to_out(crud.create_task(db, data))


@app.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskOut:
    """Obtiene una tarea por id."""
    return _to_out(_get_or_404(db, task_id))


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, data: TaskUpdate, db: Session = Depends(get_db)
) -> TaskOut:
    """Actualiza una tarea (por ejemplo, marcarla como completada)."""
    return _to_out(crud.update_task(db, _get_or_404(db, task_id), data))


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)) -> Response:
    """Elimina una tarea."""
    crud.delete_task(db, _get_or_404(db, task_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
