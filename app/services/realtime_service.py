import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Subscription:
    user_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None


class WebSocketConnectionManager:
    """Process-local WebSocket registry with project/task filtering."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, Subscription] = {}
        self._connection_loops: dict[WebSocket, asyncio.AbstractEventLoop] = {}

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket, subscription: Subscription) -> None:
        await websocket.accept()
        self._connections[websocket] = subscription
        self._connection_loops[websocket] = asyncio.get_running_loop()

    async def disconnect(self, websocket: WebSocket) -> None:
        self._connections.pop(websocket, None)
        self._connection_loops.pop(websocket, None)

    def _matches(self, subscription: Subscription, payload: dict[str, Any]) -> bool:
        if payload.get("user_id") is not None:
            return payload["user_id"] == subscription.user_id
        if payload.get("task_id") is not None and payload["task_id"] == subscription.task_id:
            return True
        return payload.get("project_id") is not None and payload["project_id"] == subscription.project_id

    async def broadcast(self, payload: dict[str, Any]) -> None:
        failed: list[WebSocket] = []
        for websocket, subscription in list(self._connections.items()):
            if not self._matches(subscription, payload):
                continue
            try:
                await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, OSError):
                failed.append(websocket)
            except Exception:
                logger.exception("Unexpected WebSocket broadcast failure")
                failed.append(websocket)
        for websocket in failed:
            await self.disconnect(websocket)

    def publish(self, payload: dict[str, Any]) -> None:
        """Schedule delivery without retaining a request or database session."""
        for websocket, loop in list(self._connection_loops.items()):
            if websocket not in self._connections or loop.is_closed():
                continue
            coroutine = self._send_if_matching(websocket, payload)
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            if running_loop is loop:
                loop.create_task(coroutine)
            else:
                asyncio.run_coroutine_threadsafe(coroutine, loop)

    async def _send_if_matching(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        subscription = self._connections.get(websocket)
        if subscription is None or not self._matches(subscription, payload):
            return
        try:
            await websocket.send_json(payload)
        except (WebSocketDisconnect, RuntimeError, OSError):
            await self.disconnect(websocket)
        except Exception:
            logger.exception("Unexpected WebSocket broadcast failure")
            await self.disconnect(websocket)


connection_manager = WebSocketConnectionManager()


def queue_realtime_event(db: Session, payload: dict[str, Any]) -> None:
    """Queue a plain event for delivery only after the current transaction commits."""
    db.info.setdefault("realtime_events", []).append(payload)


@event.listens_for(Session, "after_commit")
def _publish_committed_events(session: Session) -> None:
    for payload in session.info.pop("realtime_events", []):
        connection_manager.publish(payload)