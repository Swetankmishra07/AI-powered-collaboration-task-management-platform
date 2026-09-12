from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.database.models import Project, ProjectMember, Task, User
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate
from app.services.activity_service import record_activity
from app.services.project_service import can_manage_project, can_view_project, get_project_or_404


def _ensure_project_access(project_id: Optional[int], user: User, db: Session) -> Optional[Project]:
    if project_id is None:
        return None
    project = get_project_or_404(project_id, db)
    if not can_view_project(project, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this project.")
    return project


def _can_assign(user: User, project: Optional[Project], db: Session) -> bool:
    if user.role == "admin":
        return True
    if project is None:
        return user.role == "manager"
    return can_manage_project(project, user, db)


def _ensure_assignee(
    assignee_id: Optional[int],
    project: Optional[Project],
    current_user: User,
    db: Session,
) -> None:
    if not _can_assign(current_user, project, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to assign tasks.")
    if assignee_id is None:
        return
    if db.query(User).filter(User.id == assignee_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found.")
    if project is not None and db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == assignee_id,
    ).first() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be a project member.")


def _visible_project_ids(current_user: User, db: Session) -> List[int]:
    return [
        project.id
        for project in db.query(Project).all()
        if can_view_project(project, current_user, db)
    ]


class TaskService:
    """Task CRUD, scope authorization, assignment, and query behavior."""

    @staticmethod
    def create_task(task_data: TaskCreate, current_user: User, db: Session) -> Task:
        project = _ensure_project_access(task_data.project_id, current_user, db)
        if task_data.assignee_id is not None:
            _ensure_assignee(task_data.assignee_id, project, current_user, db)
        new_task = Task(
            title=task_data.title,
            description=task_data.description,
            status=task_data.status.value,
            priority=task_data.priority.value,
            deadline=task_data.deadline,
            creator_id=current_user.id,
            assignee_id=task_data.assignee_id,
            project_id=task_data.project_id,
        )
        try:
            db.add(new_task)
            db.flush()
            record_activity(
                db,
                actor=current_user,
                action="task_created",
                entity_type="task",
                entity_id=new_task.id,
                task_id=new_task.id,
                metadata={"project_id": new_task.project_id, "assignee_id": new_task.assignee_id},
                notifications=[{
                    "user_id": new_task.assignee_id,
                    "notification_type": "task_assigned",
                    "title": "Task assigned",
                    "message": f"You were assigned task '{new_task.title}'.",
                    "related_entity_type": "task",
                    "related_entity_id": new_task.id,
                    "task_id": new_task.id,
                }] if new_task.assignee_id and new_task.assignee_id != current_user.id else None,
            )
            db.commit()
            db.refresh(new_task)
        except Exception:
            db.rollback()
            raise
        return new_task

    @staticmethod
    def get_user_tasks(
        current_user: User,
        db: Session,
        *,
        limit: int = 50,
        offset: int = 0,
        task_status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        assignee_id: Optional[int] = None,
        project_id: Optional[int] = None,
        deadline_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Task]:
        query = db.query(Task)
        if current_user.role != "admin":
            visible_project_ids = _visible_project_ids(current_user, db)
            unscoped_access = Task.project_id.is_(None) & (
                (Task.creator_id == current_user.id)
                | (Task.assignee_id == current_user.id)
                | (Task.creator_id.is_not(None) if current_user.role == "manager" else False)
            )
            scoped_access = Task.project_id.in_(visible_project_ids) if visible_project_ids else False
            query = query.filter(or_(unscoped_access, scoped_access))

        if project_id is not None:
            _ensure_project_access(project_id, current_user, db)
            query = query.filter(Task.project_id == project_id)
        if task_status is not None:
            query = query.filter(Task.status == task_status.value)
        if priority is not None:
            query = query.filter(Task.priority == priority.value)
        if assignee_id is not None:
            query = query.filter(Task.assignee_id == assignee_id)
        if deadline_before is not None:
            query = query.filter(Task.deadline <= deadline_before)
        if deadline_after is not None:
            query = query.filter(Task.deadline >= deadline_after)
        if search:
            term = f"%{search}%"
            query = query.filter(or_(Task.title.ilike(term), Task.description.ilike(term)))

        sort_column = {
            "created_at": Task.created_at,
            "updated_at": Task.updated_at,
            "deadline": Task.deadline,
            "title": Task.title,
            "status": Task.status,
            "priority": Task.priority,
        }[sort_by]
        ordering = desc(sort_column) if sort_order == "desc" else asc(sort_column)
        return query.order_by(ordering.nullslast(), Task.id.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_task_by_id(task_id: int, current_user: User, db: Session) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with ID {task_id} not found.")

        if task.project_id is not None:
            project = get_project_or_404(task.project_id, db)
            has_access = can_view_project(project, current_user, db)
        else:
            has_access = (
                current_user.role in {"admin", "manager"}
                or task.creator_id == current_user.id
                or task.assignee_id == current_user.id
            )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access or modify this task.",
            )
        return task

    @staticmethod
    def update_task(task_id: int, task_data: TaskUpdate, current_user: User, db: Session) -> Task:
        task = TaskService.get_task_by_id(task_id, current_user, db)
        update_data = task_data.model_dump(exclude_unset=True)
        target_project = task.project
        changes = {}
        notifications = []

        if "project_id" in update_data and update_data["project_id"] != task.project_id:
            previous_project_id = task.project_id
            if task.project_id is not None:
                old_project = get_project_or_404(task.project_id, db)
                if not can_manage_project(old_project, current_user, db):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot move this task.")
            target_project = _ensure_project_access(update_data["project_id"], current_user, db)
            if target_project is not None and not can_manage_project(target_project, current_user, db):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot move tasks into this project.")
            task.project_id = update_data["project_id"]
            changes["project_id"] = {"from": previous_project_id, "to": update_data["project_id"]}
            changes["project_id"] = {"from": task.project_id, "to": update_data["project_id"]}

        if "assignee_id" in update_data:
            _ensure_assignee(update_data["assignee_id"], target_project, current_user, db)
            changes["assignee_id"] = {"from": task.assignee_id, "to": update_data["assignee_id"]}
            if update_data["assignee_id"] and update_data["assignee_id"] != current_user.id:
                notifications.append({
                    "user_id": update_data["assignee_id"],
                    "notification_type": "task_reassigned",
                    "title": "Task reassigned",
                    "message": f"Task '{task.title}' was assigned to you.",
                    "related_entity_type": "task",
                    "related_entity_id": task.id,
                    "task_id": task.id,
                })
            task.assignee_id = update_data["assignee_id"]
        if "title" in update_data and update_data["title"] is not None:
            changes["title"] = {"from": task.title, "to": update_data["title"]}
            task.title = update_data["title"]
        if "description" in update_data:
            changes["description"] = {"from": task.description, "to": update_data["description"]}
            task.description = update_data["description"]
        if "status" in update_data and update_data["status"] is not None:
            changes["status"] = {"from": task.status, "to": update_data["status"].value}
            task.status = update_data["status"].value
        if "priority" in update_data and update_data["priority"] is not None:
            changes["priority"] = {"from": task.priority, "to": update_data["priority"].value}
            task.priority = update_data["priority"].value
        if "deadline" in update_data:
            changes["deadline"] = {"from": task.deadline.isoformat() if task.deadline else None, "to": update_data["deadline"].isoformat() if update_data["deadline"] else None}
            task.deadline = update_data["deadline"]
            if task.assignee_id and task.assignee_id != current_user.id and update_data["deadline"]:
                notifications.append({
                    "user_id": task.assignee_id,
                    "notification_type": "task_deadline_changed",
                    "title": "Task deadline changed",
                    "message": f"The deadline for task '{task.title}' was changed.",
                    "related_entity_type": "task",
                    "related_entity_id": task.id,
                    "task_id": task.id,
                })

        try:
            if changes:
                record_activity(
                    db,
                    actor=current_user,
                    action="task_updated",
                    entity_type="task",
                    entity_id=task.id,
                    task_id=task.id,
                    metadata=changes,
                    notifications=notifications or None,
                )
            db.commit()
            db.refresh(task)
        except Exception:
            db.rollback()
            raise
        return task

    @staticmethod
    def delete_task(task_id: int, current_user: User, db: Session) -> None:
        task = TaskService.get_task_by_id(task_id, current_user, db)
        try:
            record_activity(
                db,
                actor=current_user,
                action="task_deleted",
                entity_type="task",
                entity_id=task.id,
                task_id=task.id,
            )
            db.delete(task)
            db.commit()
        except Exception:
            db.rollback()
            raise
