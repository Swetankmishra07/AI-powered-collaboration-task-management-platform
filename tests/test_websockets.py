import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.services.realtime_service import Subscription, WebSocketConnectionManager


def register_and_login(client, username, email):
    assert client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "StrongPassword123"},
    ).status_code == 201
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_websocket_requires_valid_access_token(client):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/ws"):
            pass
    assert error.value.code == 1008


def test_websocket_rejects_user_without_task_access(client):
    owner_token = register_and_login(client, "wsowner", "wsowner@example.com")
    outsider_token = register_and_login(client, "wsoutsider", "wsoutsider@example.com")
    task = client.post(
        "/tasks",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"title": "Private WebSocket task"},
    ).json()

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/ws?token={outsider_token}&task_id={task['id']}"):
            pass
    assert error.value.code == 1008


def test_project_scope_authorization_and_broadcast(client):
    owner_token = register_and_login(client, "wsprojectowner", "wsprojectowner@example.com")
    outsider_token = register_and_login(client, "wsprojectoutsider", "wsprojectoutsider@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    team = client.post("/teams", headers=owner_headers, json={"name": "WebSocket Team"}).json()
    project = client.post(
        "/projects",
        headers=owner_headers,
        json={"team_id": team["id"], "name": "WebSocket Project"},
    ).json()

    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"/ws?token={outsider_token}&project_id={project['id']}"):
            pass
    assert error.value.code == 1008

    with client.websocket_connect(f"/ws?token={owner_token}&project_id={project['id']}") as websocket:
        task = client.post(
            "/tasks",
            headers=owner_headers,
            json={"title": "Project realtime task", "project_id": project["id"]},
        )
        assert task.status_code == 201
        events = [websocket.receive_json(), websocket.receive_json()]

    assert {event["type"] for event in events} == {"task.created", "activity"}
    assert all(event["project_id"] == project["id"] for event in events)


def test_task_scope_receives_task_and_activity_events(client):
    token = register_and_login(client, "wstaskuser", "wstaskuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    task = client.post("/tasks", headers=headers, json={"title": "Realtime task"}).json()

    with client.websocket_connect(f"/ws?token={token}&task_id={task['id']}") as websocket:
        response = client.put(
            f"/tasks/{task['id']}",
            headers=headers,
            json={"title": "Updated realtime task"},
        )
        assert response.status_code == 200
        events = [websocket.receive_json(), websocket.receive_json()]

    assert {event["type"] for event in events} == {"task.updated", "activity"}
    assert all(event["task_id"] == task["id"] for event in events)


def test_user_scope_receives_notification_event(client):
    owner_token = register_and_login(client, "wsnotifyowner", "wsnotifyowner@example.com")
    assignee_token = register_and_login(client, "wsnotifyassignee", "wsnotifyassignee@example.com")
    assignee_headers = {"Authorization": f"Bearer {assignee_token}"}
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    from app.database.database import SessionLocal
    from app.database.models import User

    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.email == "wsnotifyowner@example.com").one()
        owner.role = "manager"
        assignee_id = db.query(User).filter(User.email == "wsnotifyassignee@example.com").one().id
        db.commit()
    finally:
        db.close()

    task = client.post("/tasks", headers=owner_headers, json={"title": "Notification task"}).json()
    with client.websocket_connect(f"/ws?token={assignee_token}") as websocket:
        response = client.put(
            f"/tasks/{task['id']}",
            headers=owner_headers,
            json={"assignee_id": assignee_id},
        )
        assert response.status_code == 200
        event = websocket.receive_json()

    assert event["type"] == "notification"
    assert event["user_id"] == assignee_id
    assert event["notification_type"] == "task_reassigned"


def test_websocket_ping_and_disconnect_cleanup(client):
    token = register_and_login(client, "wspinguser", "wspinguser@example.com")
    from app.services.realtime_service import connection_manager

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_text("ping")
        assert websocket.receive_json() == {"type": "pong"}
        assert connection_manager.connection_count == 1
    assert connection_manager.connection_count == 0


def test_manager_removes_failed_connections():
    class BrokenSocket:
        async def send_json(self, _payload):
            raise RuntimeError("socket closed")

    manager = WebSocketConnectionManager()
    socket = BrokenSocket()
    manager._connections[socket] = Subscription(user_id=1, task_id=7)

    asyncio.run(manager.broadcast({"type": "task.updated", "task_id": 7}))

    assert manager.connection_count == 0