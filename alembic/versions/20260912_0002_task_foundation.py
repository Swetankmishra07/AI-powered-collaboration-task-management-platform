"""Add collaborative task foundation fields and constraints.

Revision ID: 20260912_0002
Revises: 20260912_0001
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0002"
down_revision: Union[str, None] = "20260912_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("users", recreate="always") as batch_op:
            batch_op.add_column(
                sa.Column("role", sa.String(length=20), server_default="member", nullable=False)
            )
            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=False,
                )
            )
            batch_op.create_check_constraint(
                "ck_users_role",
                "role IN ('admin', 'manager', 'member')",
            )

        with op.batch_alter_table("tasks", recreate="always") as batch_op:
            batch_op.alter_column(
                "user_id",
                new_column_name="creator_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
            )
            batch_op.add_column(
                sa.Column("priority", sa.String(length=20), server_default="low", nullable=False)
            )
            batch_op.add_column(sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column("assignee_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tasks_assignee_id_users",
                "users",
                ["assignee_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.create_check_constraint(
                "ck_tasks_status",
                "status IN ('todo', 'pending', 'in_progress', 'blocked', 'completed')",
            )
            batch_op.create_check_constraint(
                "ck_tasks_priority",
                "priority IN ('low', 'medium', 'high', 'critical')",
            )
    else:
        op.add_column(
            "users",
            sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        )
        op.add_column(
            "users",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
        op.create_check_constraint(
            "ck_users_role", "users", "role IN ('admin', 'manager', 'member')"
        )
        op.alter_column(
            "tasks",
            "user_id",
            new_column_name="creator_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        op.add_column(
            "tasks",
            sa.Column("priority", sa.String(length=20), server_default="low", nullable=False),
        )
        op.add_column("tasks", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
        op.add_column("tasks", sa.Column("assignee_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_tasks_assignee_id_users",
            "tasks",
            "users",
            ["assignee_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_check_constraint(
            "ck_tasks_status",
            "tasks",
            "status IN ('todo', 'pending', 'in_progress', 'blocked', 'completed')",
        )
        op.create_check_constraint(
            "ck_tasks_priority",
            "tasks",
            "priority IN ('low', 'medium', 'high', 'critical')",
        )

    op.execute(sa.text("UPDATE tasks SET status = 'todo' WHERE status = 'pending'"))
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.create_index("ix_tasks_creator_id", "tasks", ["creator_id"], unique=False)
    op.create_index("ix_tasks_deadline", "tasks", ["deadline"], unique=False)
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_assignee_id", table_name="tasks")
    op.drop_index("ix_tasks_deadline", table_name="tasks")
    op.drop_index("ix_tasks_creator_id", table_name="tasks")
    if op.get_context().dialect.name == "sqlite":
        with op.batch_alter_table("tasks", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_tasks_priority", type_="check")
            batch_op.drop_constraint("ck_tasks_status", type_="check")
            batch_op.drop_constraint("fk_tasks_assignee_id_users", type_="foreignkey")
            batch_op.drop_column("assignee_id")
            batch_op.drop_column("deadline")
            batch_op.drop_column("priority")
            batch_op.alter_column(
                "creator_id",
                new_column_name="user_id",
                existing_type=sa.Integer(),
                existing_nullable=False,
            )
        op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)

        with op.batch_alter_table("users", recreate="always") as batch_op:
            batch_op.drop_constraint("ck_users_role", type_="check")
            batch_op.drop_column("updated_at")
            batch_op.drop_column("role")
    else:
        op.drop_constraint("ck_tasks_priority", "tasks", type_="check")
        op.drop_constraint("ck_tasks_status", "tasks", type_="check")
        op.drop_constraint("fk_tasks_assignee_id_users", "tasks", type_="foreignkey")
        op.drop_column("tasks", "assignee_id")
        op.drop_column("tasks", "deadline")
        op.drop_column("tasks", "priority")
        op.alter_column(
            "tasks",
            "creator_id",
            new_column_name="user_id",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
        op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)
        op.drop_constraint("ck_users_role", "users", type_="check")
        op.drop_column("users", "updated_at")
        op.drop_column("users", "role")