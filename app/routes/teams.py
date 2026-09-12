from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.team import TeamCreate, TeamMemberCreate, TeamMemberResponse, TeamResponse, TeamUpdate
from app.services.team_service import TeamService


router = APIRouter(prefix="/teams", tags=["Teams"])


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(team_data: TeamCreate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.create_team(team_data, current_user, db)


@router.get("", response_model=List[TeamResponse])
def list_teams(current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.list_teams(current_user, db)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.get_team(team_id, current_user, db)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(team_id: int, team_data: TeamUpdate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.update_team(team_id, team_data, current_user, db)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(team_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    TeamService.delete_team(team_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
def list_team_members(team_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.list_members(team_id, current_user, db)


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
def add_team_member(team_id: int, member_data: TeamMemberCreate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return TeamService.add_member(team_id, member_data, current_user, db)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(team_id: int, user_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    TeamService.remove_member(team_id, user_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)