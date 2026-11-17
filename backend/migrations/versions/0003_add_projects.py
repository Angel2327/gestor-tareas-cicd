"""Agregar proyectos y relación tarea -> proyecto

Cambio compatible hacia atrás (expand): tabla nueva y columna project_id
opcional. La versión anterior de la app sigue funcionando si hay rollback.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_projects_name"),
    )
    # batch_alter_table permite que la misma migración funcione en SQLite (pruebas)
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_tasks_project_id",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_tasks_project_id", ["project_id"])


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_project_id")
        batch.drop_constraint("fk_tasks_project_id", type_="foreignkey")
        batch.drop_column("project_id")
    op.drop_table("projects")
