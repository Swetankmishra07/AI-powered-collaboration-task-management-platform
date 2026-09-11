import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_headers(username: str, email: str):
    client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "Password123"}
    )
    res = client.post(
        "/auth/login",
        json={"email": email, "password": "Password123"}
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_task():
    headers = get_auth_headers("t_user1", "t_user1@example.com")
    response = client.post(
        "/tasks",
        json={
            "title": "Learn FastAPI CRUD",
            "description": "Complete Task Management API",
            "status": "pending"
        },
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Learn FastAPI CRUD"
    assert data["status"] == "pending"
    assert "id" in data


def test_get_user_tasks():
    headers = get_auth_headers("t_user2", "t_user2@example.com")
    client.post(
        "/tasks",
        json={"title": "Task A", "status": "pending"},
        headers=headers
    )
    client.post(
        "/tasks",
        json={"title": "Task B", "status": "in_progress"},
        headers=headers
    )
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_ownership_authorization_protection():
    headers_owner = get_auth_headers("owner_user", "owner@example.com")
    headers_stranger = get_auth_headers("stranger_user", "stranger@example.com")

    # Owner creates task
    task_res = client.post(
        "/tasks",
        json={"title": "Owner Secret Task", "status": "pending"},
        headers=headers_owner
    )
    task_id = task_res.json()["id"]

    # Stranger attempts GET
    get_res = client.get(f"/tasks/{task_id}", headers=headers_stranger)
    assert get_res.status_code == 403

    # Stranger attempts PUT
    put_res = client.put(f"/tasks/{task_id}", json={"title": "Hacked"}, headers=headers_stranger)
    assert put_res.status_code == 403

    # Stranger attempts DELETE
    del_res = client.delete(f"/tasks/{task_id}", headers=headers_stranger)
    assert del_res.status_code == 403


def test_delete_task_success():
    headers = get_auth_headers("del_user", "del@example.com")
    task_res = client.post(
        "/tasks",
        json={"title": "Task to be deleted", "status": "pending"},
        headers=headers
    )
    task_id = task_res.json()["id"]

    # Delete task
    del_res = client.delete(f"/tasks/{task_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify task is deleted
    get_res = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_res.status_code == 404
