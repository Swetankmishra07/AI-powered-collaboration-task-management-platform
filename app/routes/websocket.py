import logging
from typing import Optional

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.database import SessionLocal
from app.database.models import Project, Task, User
from app.services.project_service import can_view_project
from app.services.realtime_service import Subscription, connection_manager


logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


def _token_from_websocket(websocket: WebSocket) -> Optional[str]:
    token = websocket.query_params.get("token")
    if token:
        return token
    authorization = websocket.headers.get("authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value:
        return value
    return None


def _authenticate(token: Optional[str], db: Session) -> User:
    if not token:
        raise ValueError("Missing WebSocket token")
    try:
        payload = decode_access_token(token)
        if payload.get("typ") != "access":
            raise ValueError("Invalid token type")
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid WebSocket token") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError("Unknown WebSocket user")
    return user


def _authorize_scope(
    user: User,
    db: Session,
    project_id: Optional[int],
    task_id: Optional[int],
) -> Subscription:
    if project_id is None and task_id is None:
        return Subscription(user_id=user.id)

    if project_id is not None:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None or not can_view_project(project, user, db):
            raise PermissionError("Project access denied")

    if task_id is not None:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            raise PermissionError("Task access denied")
        if project_id is not None and task.project_id != project_id:
            raise PermissionError("Task does not belong to project")
        if task.project_id is not None:
            project = db.query(Project).filter(Project.id == task.project_id).first()
            allowed = project is not None and can_view_project(project, user, db)
        else:
            allowed = (
                user.role in {"admin", "manager"}
                or task.creator_id == user.id
                or task.assignee_id == user.id
            )
        if not allowed:
            raise PermissionError("Task access denied")

    return Subscription(user_id=user.id, project_id=project_id, task_id=task_id)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: Optional[int] = Query(default=None),
    task_id: Optional[int] = Query(default=None),
) -> None:
    db = SessionLocal()
    try:
        user = _authenticate(_token_from_websocket(websocket), db)
        subscription = _authorize_scope(user, db, project_id, task_id)
    except (ValueError, PermissionError):
        db.close()
        await websocket.close(code=1008)
        return
    except Exception:
        db.close()
        logger.exception("WebSocket authentication failed")
        await websocket.close(code=1011)
        return
    finally:
        if db.is_active:
            db.close()

    await connection_manager.connect(websocket, subscription)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket connection failed")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        await connection_manager.disconnect(websocket)