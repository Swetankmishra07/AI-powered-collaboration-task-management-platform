from app.database.database import SessionLocal
from app.database.models import User


def register_and_login(client, username, email, password="StrongPassword123"):
    registration = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert registration.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def assign_role(email, role):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        user.role = role
        db.commit()
    finally:
        db.close()


def test_member_can_access_owned_task_but_not_user_management(client):
    member_headers = register_and_login(client, "member", "member@example.com")

    task = client.post(
        "/tasks",
        headers=member_headers,
        json={"title": "Member task", "status": "todo"},
    )
    users = client.get("/users", headers=member_headers)

    assert task.status_code == 201
    assert users.status_code == 403


def test_manager_can_manage_current_task_scope(client):
    owner_headers = register_and_login(client, "owner", "owner@example.com")
    task = client.post(
        "/tasks",
        headers=owner_headers,
        json={"title": "Managed task", "status": "todo"},
    )
    task_id = task.json()["id"]

    manager_headers = register_and_login(client, "manager", "manager@example.com")
    assign_role("manager@example.com", "manager")

    users = client.get("/users", headers=manager_headers)
    managed_task = client.get(f"/tasks/{task_id}", headers=manager_headers)
    updated = client.put(
        f"/tasks/{task_id}",
        headers=manager_headers,
        json={"title": "Manager updated task"},
    )

    assert users.status_code == 200
    assert managed_task.status_code == 200
    assert updated.status_code == 200


def test_admin_can_change_user_roles(client):
    admin_headers = register_and_login(client, "admin", "admin@example.com")
    assign_role("admin@example.com", "admin")
    register_and_login(client, "promote", "promote@example.com")

    target = client.get("/users", headers=admin_headers).json()
    target_id = next(user["id"] for user in target if user["email"] == "promote@example.com")
    response = client.patch(
        f"/users/{target_id}/role",
        headers=admin_headers,
        json={"role": "manager"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "manager"


def test_member_cannot_escalate_role(client):
    member_headers = register_and_login(client, "escalator", "escalator@example.com")

    response = client.patch(
        "/users/1/role",
        headers=member_headers,
        json={"role": "admin"},
    )

    assert response.status_code == 403


def test_registration_cannot_assign_privileged_role(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "untrusted",
            "email": "untrusted@example.com",
            "password": "StrongPassword123",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "member"


def test_unauthenticated_users_cannot_access_rbac_or_tasks(client):
    users = client.get("/users")
    tasks = client.get("/tasks")

    assert users.status_code == 401
    assert tasks.status_code == 401
