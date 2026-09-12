"""Add teams, projects, and scoped memberships.

Revision ID: 20260912_0004
Revises: 20260912_0003
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260912_0004"
down_revision: Union[str, None] = "20260912_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_teams_id", "teams", ["id"], unique=False)
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"], unique=False)

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('manager', 'member')", name="ck_team_members_role"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )
    op.create_index("ix_team_members_id", "team_members", ["id"], unique=False)
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"], unique=False)
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "name", name="uq_projects_team_name"),
    )
    op.create_index("ix_projects_id", "projects", ["id"], unique=False)
    op.create_index("ix_projects_team_id", "projects", ["team_id"], unique=False)
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("role IN ('manager', 'member')", name="ck_project_members_role"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_id", "project_members", ["id"], unique=False)
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"], unique=False)
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_members_user_id", table_name="project_members")
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_index("ix_project_members_id", table_name="project_members")
    op.drop_table("project_members")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_index("ix_projects_team_id", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_index("ix_team_members_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_teams_owner_id", table_name="teams")
    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_table("teams")