from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.database.models import Task, User
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """
    Business Logic Service for Task CRUD Operations & Ownership Authorization.
    """

    @staticmethod
    def create_task(task_data: TaskCreate, current_user: User, db: Session) -> Task:
        """
        Creates a new task associated strictly with the authenticated current_user.
        """
        new_task = Task(
            title=task_data.title,
            description=task_data.description,
            status=task_data.status.value,
            user_id=current_user.id  # Sets ownership
        )

        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task

    @staticmethod
    def get_user_tasks(current_user: User, db: Session) -> List[Task]:
        """
        Retrieves all tasks belonging strictly to current_user.
        Prevents unauthorized access to other users' tasks.
        """
        return db.query(Task).filter(Task.user_id == current_user.id).all()

    @staticmethod
    def get_task_by_id(task_id: int, current_user: User, db: Session) -> Task:
        """
        Retrieves a single task by ID.
        Verifies task existence (404) and task ownership authorization (403).
        """
        task = db.query(Task).filter(Task.id == task_id).first()

        # 1. Existence Check
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found."
            )

        # 2. Ownership Authorization Check
        if task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access or modify this task."
            )

        return task

    @staticmethod
    def update_task(task_id: int, task_data: TaskUpdate, current_user: User, db: Session) -> Task:
        """
        Updates an existing task after ownership authorization check.
        """
        task = TaskService.get_task_by_id(task_id, current_user, db)

        if task_data.title is not None:
            task.title = task_data.title
        if task_data.description is not None:
            task.description = task_data.description
        if task_data.status is not None:
            task.status = task_data.status.value

        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete_task(task_id: int, current_user: User, db: Session) -> None:
        """
        Deletes a task after ownership authorization check.
        """
        task = TaskService.get_task_by_id(task_id, current_user, db)
        db.delete(task)
        db.commit()
