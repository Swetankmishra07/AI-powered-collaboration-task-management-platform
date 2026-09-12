from app.database.database import SessionLocal
from app.database.models import Notification, User


def register_and_login(client, username, email):
    assert client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "StrongPassword123"},
    ).status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def user_id_for(email):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).one().id
    finally:
        db.close()


def set_role(email, role):
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email).one().role = role
        db.commit()
    finally:
        db.close()


def test_assignment_comment_and_membership_notifications(client):
    owner = register_and_login(client, "notifyowner", "notifyowner@example.com")
    assignee = register_and_login(client, "notifyassignee", "notifyassignee@example.com")
    manager = register_and_login(client, "notifymanager", "notifymanager@example.com")
    set_role("notifymanager@example.com", "manager")
    assignee_id = user_id_for("notifyassignee@example.com")

    task = client.post("/tasks", headers=owner, json={"title": "Notify task"})
    task_id = task.json()["id"]
    assignment = client.put(
        f"/tasks/{task_id}",
        headers=manager,
        json={"assignee_id": assignee_id},
    )
    comment = client.post(
        f"/tasks/{task_id}/comments",
        headers=owner,
        json={"body": "A comment for the assignee"},
    )
    notifications = client.get("/notifications", headers=assignee).json()

    assert assignment.status_code == 200
    assert comment.status_code == 201
    assert any(item["type"] == "task_reassigned" for item in notifications)
    assert any(item["type"] == "comment_added" for item in notifications)


def test_team_and_project_membership_notifications(client):
    owner = register_and_login(client, "notificationowner", "notificationowner@example.com")
    member = register_and_login(client, "notificationmember", "notificationmember@example.com")
    member_id = user_id_for("notificationmember@example.com")

    team = client.post("/teams", headers=owner, json={"name": "Notification Team"})
    team_id = team.json()["id"]
    team_member = client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": member_id},
    )
    project = client.post(
        "/projects",
        headers=owner,
        json={"team_id": team_id, "name": "Notification Project"},
    )
    project_member = client.post(
        f"/projects/{project.json()['id']}/members",
        headers=owner,
        json={"user_id": member_id},
    )
    notifications = client.get("/notifications", headers=member).json()

    assert team_member.status_code == 201
    assert project_member.status_code == 201
    assert any(item["type"] == "team_member_added" for item in notifications)
    assert any(item["type"] == "project_member_added" for item in notifications)


def test_notification_read_state_and_user_isolation(client):
    owner = register_and_login(client, "readowner", "readowner@example.com")
    other = register_and_login(client, "readother", "readother@example.com")
    manager = register_and_login(client, "readmanager", "readmanager@example.com")
    set_role("readmanager@example.com", "manager")
    task = client.post("/tasks", headers=owner, json={"title": "Read task"})
    client.put(
        f"/tasks/{task.json()['id']}",
        headers=manager,
        json={"assignee_id": user_id_for("readother@example.com")},
    )
    client.post(f"/tasks/{task.json()['id']}/comments", headers=other, json={"body": "Other comment"})
    owner_notifications = client.get("/notifications", headers=owner).json()
    notification_id = owner_notifications[0]["id"]

    unread = client.get("/notifications?unread_only=true", headers=owner)
    marked = client.patch(f"/notifications/{notification_id}/read", headers=owner)
    unread_after = client.get("/notifications?unread_only=true", headers=owner)
    forbidden = client.patch(f"/notifications/{notification_id}/read", headers=other)
    all_read = client.post("/notifications/read-all", headers=owner)

    assert unread.status_code == 200
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert unread_after.json() == []
    assert forbidden.status_code == 403
    assert all_read.status_code == 204


def test_notification_delete_is_owner_scoped(client):
    owner = register_and_login(client, "deleteowner", "deleteowner@example.com")
    other = register_and_login(client, "deleteother", "deleteother@example.com")
    manager = register_and_login(client, "deletemanager", "deletemanager@example.com")
    set_role("deletemanager@example.com", "manager")
    task = client.post("/tasks", headers=owner, json={"title": "Delete notification task"})
    client.put(
        f"/tasks/{task.json()['id']}",
        headers=manager,
        json={"assignee_id": user_id_for("deleteother@example.com")},
    )
    client.post(f"/tasks/{task.json()['id']}/comments", headers=other, json={"body": "Other note"})
    notification_id = client.get("/notifications", headers=owner).json()[0]["id"]

    forbidden = client.delete(f"/notifications/{notification_id}", headers=other)
    deleted = client.delete(f"/notifications/{notification_id}", headers=owner)

    assert forbidden.status_code == 403
    assert deleted.status_code == 204
