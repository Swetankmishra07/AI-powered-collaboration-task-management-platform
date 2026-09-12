"""Add task comments and append-only activity logs.

Revision ID: 20260912_0006
Revises: 20260912_0005
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0006"
down_revision: Union[str, None] = "20260912_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_id", "comments", ["id"], unique=False)
    op.create_index("ix_comments_task_id", "comments", ["task_id"], unique=False)
    op.create_index("ix_comments_author_id", "comments", ["author_id"], unique=False)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_id", "activity_logs", ["id"], unique=False)
    op.create_index("ix_activity_logs_actor_id", "activity_logs", ["actor_id"], unique=False)
    op.create_index("ix_activity_logs_task_id", "activity_logs", ["task_id"], unique=False)
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"], unique=False)
    op.create_index("ix_activity_logs_entity_type", "activity_logs", ["entity_type"], unique=False)
    op.create_index("ix_activity_logs_entity_id", "activity_logs", ["entity_id"], unique=False)
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"], unique=False)


def downgrade() -> None:
    for index_name in (
        "ix_activity_logs_created_at",
        "ix_activity_logs_entity_id",
        "ix_activity_logs_entity_type",
        "ix_activity_logs_action",
        "ix_activity_logs_task_id",
        "ix_activity_logs_actor_id",
        "ix_activity_logs_id",
    ):
        op.drop_index(index_name, table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_task_id", table_name="comments")
    op.drop_index("ix_comments_id", table_name="comments")
    op.drop_table("comments")