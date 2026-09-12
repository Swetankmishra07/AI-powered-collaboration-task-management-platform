from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import Project, ProjectMember, TeamMember, User
from app.schemas.project import ProjectCreate, ProjectMemberCreate, ProjectUpdate
from app.services.team_service import (
    ensure_team_manage_access,
    get_team_or_404,
    is_team_manager,
)
from app.services.activity_service import record_activity


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


def can_manage_project(project: Project, user: User, db: Session) -> bool:
    if user.role == "admin" or project.owner_id == user.id:
        return True
    return is_team_manager(project.team, user, db)


def can_view_project(project: Project, user: User, db: Session) -> bool:
    if can_manage_project(project, user, db):
        return True
    return db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
    ).first() is not None


def ensure_project_view_access(project: Project, user: User, db: Session) -> None:
    if not can_view_project(project, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project.",
        )


def ensure_project_manage_access(project: Project, user: User, db: Session) -> None:
    if not can_manage_project(project, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this project.",
        )


class ProjectService:
    @staticmethod
    def create_project(project_data: ProjectCreate, current_user: User, db: Session) -> Project:
        team = get_team_or_404(project_data.team_id, db)
        ensure_team_manage_access(team, current_user, db)
        project = Project(
            team_id=team.id,
            owner_id=current_user.id,
            name=project_data.name,
            description=project_data.description,
        )
        db.add(project)
        db.flush()
        db.add(ProjectMember(project_id=project.id, user_id=current_user.id, role="manager"))
        record_activity(db, actor=current_user, action="project_created", entity_type="project", entity_id=project.id, metadata={"team_id": team.id})
        try:
            db.commit()
            db.refresh(project)
        except Exception:
            db.rollback()
            raise
        return project

    @staticmethod
    def list_projects(current_user: User, db: Session) -> List[Project]:
        projects = db.query(Project).order_by(Project.id).all()
        return [project for project in projects if can_view_project(project, current_user, db)]

    @staticmethod
    def get_project(project_id: int, current_user: User, db: Session) -> Project:
        project = get_project_or_404(project_id, db)
        ensure_project_view_access(project, current_user, db)
        return project

    @staticmethod
    def update_project(
        project_id: int,
        project_data: ProjectUpdate,
        current_user: User,
        db: Session,
    ) -> Project:
        project = get_project_or_404(project_id, db)
        ensure_project_manage_access(project, current_user, db)
        values = project_data.model_dump(exclude_unset=True)
        if "name" in values and values["name"] is not None:
            project.name = values["name"]
        if "description" in values:
            project.description = values["description"]
        try:
            record_activity(db, actor=current_user, action="project_updated", entity_type="project", entity_id=project.id, metadata=values)
            db.commit()
            db.refresh(project)
        except Exception:
            db.rollback()
            raise
        return project

    @staticmethod
    def delete_project(project_id: int, current_user: User, db: Session) -> None:
        project = get_project_or_404(project_id, db)
        ensure_project_manage_access(project, current_user, db)
        try:
            record_activity(db, actor=current_user, action="project_deleted", entity_type="project", entity_id=project.id, metadata={"team_id": project.team_id})
            db.delete(project)
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list_members(project_id: int, current_user: User, db: Session) -> List[ProjectMember]:
        project = get_project_or_404(project_id, db)
        ensure_project_view_access(project, current_user, db)
        return db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id
        ).order_by(ProjectMember.id).all()

    @staticmethod
    def add_member(
        project_id: int,
        member_data: ProjectMemberCreate,
        current_user: User,
        db: Session,
    ) -> ProjectMember:
        project = get_project_or_404(project_id, db)
        ensure_project_manage_access(project, current_user, db)
        user = db.query(User).filter(User.id == member_data.user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        team_membership = db.query(TeamMember).filter(
            TeamMember.team_id == project.team_id,
            TeamMember.user_id == member_data.user_id,
        ).first()
        if team_membership is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must be a team member before joining a project.",
            )
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_data.user_id,
        ).first()
        if membership is None:
            membership = ProjectMember(
                project_id=project_id,
                user_id=member_data.user_id,
                role=member_data.role.value,
            )
            db.add(membership)
        else:
            membership.role = member_data.role.value
        try:
            record_activity(
                db,
                actor=current_user,
                action="project_member_added",
                entity_type="project",
                entity_id=project.id,
                metadata={"user_id": member_data.user_id, "role": member_data.role.value},
                notifications=[{
                    "user_id": member_data.user_id,
                    "notification_type": "project_member_added",
                    "title": "Added to project",
                    "message": f"You were added to project '{project.name}'.",
                    "related_entity_type": "project",
                    "related_entity_id": project.id,
                }] if member_data.user_id != current_user.id else None,
            )
            db.commit()
            db.refresh(membership)
        except Exception:
            db.rollback()
            raise
        return membership

    @staticmethod
    def remove_member(project_id: int, user_id: int, current_user: User, db: Session) -> None:
        project = get_project_or_404(project_id, db)
        ensure_project_manage_access(project, current_user, db)
        if project.owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project owner cannot be removed from the project.",
            )
        membership = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        ).first()
        if membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found.")
        try:
            record_activity(
                db,
                actor=current_user,
                action="project_member_removed",
                entity_type="project",
                entity_id=project.id,
                metadata={"user_id": user_id},
            )
            db.delete(membership)
            db.commit()
        except Exception:
            db.rollback()
            raise
