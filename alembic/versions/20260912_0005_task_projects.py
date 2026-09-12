"""Link tasks to projects.

Revision ID: 20260912_0005
Revises: 20260912_0004
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0005"
down_revision: Union[str, None] = "20260912_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("tasks", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("project_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tasks_project_id_projects",
                "projects",
                ["project_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.add_column("tasks", sa.Column("project_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_tasks_project_id_projects",
            "tasks",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("tasks", recreate="always") as batch_op:
            batch_op.drop_constraint("fk_tasks_project_id_projects", type_="foreignkey")
            batch_op.drop_column("project_id")
    else:
        op.drop_constraint("fk_tasks_project_id_projects", "tasks", type_="foreignkey")
        op.drop_column("tasks", "project_id")