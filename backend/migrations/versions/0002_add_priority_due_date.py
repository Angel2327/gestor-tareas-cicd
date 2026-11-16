"""Agregar prioridad y fecha límite

Cambio compatible hacia atrás (expand): columnas nuevas con valor por defecto
o nulas, para que la versión anterior de la app siga funcionando si hay rollback.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "priority", sa.String(length=10), nullable=False, server_default="medium"
        ),
    )
    op.add_column("tasks", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "due_date")
    op.drop_column("tasks", "priority")
