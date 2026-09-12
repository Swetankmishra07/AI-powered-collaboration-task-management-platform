from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import Team, TeamMember, User
from app.schemas.team import TeamCreate, TeamMemberCreate, TeamUpdate
from app.services.activity_service import record_activity


def get_team_or_404(team_id: int, db: Session) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")
    return team


def is_team_manager(team: Team, user: User, db: Session) -> bool:
    if user.role == "admin" or team.owner_id == user.id:
        return True
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id,
    ).first()
    return membership is not None and membership.role == "manager"


def can_view_team(team: Team, user: User, db: Session) -> bool:
    if user.role == "admin":
        return True
    return db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id,
    ).first() is not None


def ensure_team_view_access(team: Team, user: User, db: Session) -> None:
    if not can_view_team(team, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this team.",
        )


def ensure_team_manage_access(team: Team, user: User, db: Session) -> None:
    if not is_team_manager(team, user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this team.",
        )


class TeamService:
    @staticmethod
    def create_team(team_data: TeamCreate, current_user: User, db: Session) -> Team:
        team = Team(
            name=team_data.name,
            description=team_data.description,
            owner_id=current_user.id,
        )
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=current_user.id, role="manager"))
        record_activity(db, actor=current_user, action="team_created", entity_type="team", entity_id=team.id)
        try:
            db.commit()
            db.refresh(team)
        except Exception:
            db.rollback()
            raise
        return team

    @staticmethod
    def list_teams(current_user: User, db: Session) -> List[Team]:
        if current_user.role == "admin":
            return db.query(Team).order_by(Team.id).all()
        return (
            db.query(Team)
            .join(TeamMember)
            .filter(TeamMember.user_id == current_user.id)
            .order_by(Team.id)
            .all()
        )

    @staticmethod
    def get_team(team_id: int, current_user: User, db: Session) -> Team:
        team = get_team_or_404(team_id, db)
        ensure_team_view_access(team, current_user, db)
        return team

    @staticmethod
    def update_team(team_id: int, team_data: TeamUpdate, current_user: User, db: Session) -> Team:
        team = get_team_or_404(team_id, db)
        ensure_team_manage_access(team, current_user, db)
        values = team_data.model_dump(exclude_unset=True)
        if "name" in values and values["name"] is not None:
            team.name = values["name"]
        if "description" in values:
            team.description = values["description"]
        try:
            record_activity(db, actor=current_user, action="team_updated", entity_type="team", entity_id=team.id, metadata=values)
            db.commit()
            db.refresh(team)
        except Exception:
            db.rollback()
            raise
        return team

    @staticmethod
    def delete_team(team_id: int, current_user: User, db: Session) -> None:
        team = get_team_or_404(team_id, db)
        ensure_team_manage_access(team, current_user, db)
        try:
            record_activity(db, actor=current_user, action="team_deleted", entity_type="team", entity_id=team.id)
            db.delete(team)
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list_members(team_id: int, current_user: User, db: Session) -> List[TeamMember]:
        team = get_team_or_404(team_id, db)
        ensure_team_view_access(team, current_user, db)
        return db.query(TeamMember).filter(TeamMember.team_id == team_id).order_by(TeamMember.id).all()

    @staticmethod
    def add_member(
        team_id: int,
        member_data: TeamMemberCreate,
        current_user: User,
        db: Session,
    ) -> TeamMember:
        team = get_team_or_404(team_id, db)
        ensure_team_manage_access(team, current_user, db)
        user = db.query(User).filter(User.id == member_data.user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == member_data.user_id,
        ).first()
        if membership is None:
            membership = TeamMember(
                team_id=team_id,
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
                action="team_member_added",
                entity_type="team",
                entity_id=team.id,
                metadata={"user_id": member_data.user_id, "role": member_data.role.value},
                notifications=[{
                    "user_id": member_data.user_id,
                    "notification_type": "team_member_added",
                    "title": "Added to team",
                    "message": f"You were added to team '{team.name}'.",
                    "related_entity_type": "team",
                    "related_entity_id": team.id,
                }] if member_data.user_id != current_user.id else None,
            )
            db.commit()
            db.refresh(membership)
        except Exception:
            db.rollback()
            raise
        return membership

    @staticmethod
    def remove_member(team_id: int, user_id: int, current_user: User, db: Session) -> None:
        team = get_team_or_404(team_id, db)
        ensure_team_manage_access(team, current_user, db)
        if team.owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A team owner cannot be removed from the team.",
            )
        membership = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
        ).first()
        if membership is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found.")
        try:
            record_activity(
                db,
                actor=current_user,
                action="team_member_removed",
                entity_type="team",
                entity_id=team.id,
                metadata={"user_id": user_id},
            )
            db.delete(membership)
            db.commit()
        except Exception:
            db.rollback()
            raise
