"""Add durable user notifications.

Revision ID: 20260912_0007
Revises: 20260912_0006
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0007"
down_revision: Union[str, None] = "20260912_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=30), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_type", "notifications", ["type"], unique=False)
    op.create_index("ix_notifications_task_id", "notifications", ["task_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_task_id", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")