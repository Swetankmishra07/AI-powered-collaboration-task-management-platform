from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.project import ProjectCreate, ProjectMemberCreate, ProjectMemberResponse, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_data: ProjectCreate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.create_project(project_data, current_user, db)


@router.get("", response_model=List[ProjectResponse])
def list_projects(current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.list_projects(current_user, db)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.get_project(project_id, current_user, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, project_data: ProjectUpdate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.update_project(project_id, project_data, current_user, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    ProjectService.delete_project(project_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_project_members(project_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.list_members(project_id, current_user, db)


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(project_id: int, member_data: ProjectMemberCreate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return ProjectService.add_member(project_id, member_data, current_user, db)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(project_id: int, user_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    ProjectService.remove_member(project_id, user_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)