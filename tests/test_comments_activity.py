from app.database.database import SessionLocal
from app.database.models import ActivityLog, User


def register_and_login(client, username, email):
    response = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "StrongPassword123"},
    )
    assert response.status_code == 201
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
        user = db.query(User).filter(User.email == email).one()
        user.role = role
        db.commit()
    finally:
        db.close()


def test_comment_crud_and_task_activity(client):
    owner = register_and_login(client, "commentowner", "commentowner@example.com")
    task = client.post("/tasks", headers=owner, json={"title": "Commentable task"})
    task_id = task.json()["id"]

    created = client.post(f"/tasks/{task_id}/comments", headers=owner, json={"body": "Initial note"})
    comment_id = created.json()["id"]
    listed = client.get(f"/tasks/{task_id}/comments", headers=owner)
    updated = client.patch(f"/comments/{comment_id}", headers=owner, json={"body": "Updated note"})
    activity = client.get(f"/tasks/{task_id}/activity", headers=owner)
    deleted = client.delete(f"/comments/{comment_id}", headers=owner)

    actions = [event["action"] for event in activity.json()]
    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()[0]["body"] == "Initial note"
    assert updated.status_code == 200
    assert updated.json()["body"] == "Updated note"
    assert "task_created" in actions
    assert "comment_created" in actions
    assert "comment_updated" in actions
    assert deleted.status_code == 204


def test_comment_ownership_and_task_scope(client):
    owner = register_and_login(client, "commentauthor", "commentauthor@example.com")
    stranger = register_and_login(client, "commentstranger", "commentstranger@example.com")
    task = client.post("/tasks", headers=owner, json={"title": "Private comment task"})
    task_id = task.json()["id"]
    comment = client.post(f"/tasks/{task_id}/comments", headers=owner, json={"body": "Private"})
    comment_id = comment.json()["id"]

    create_forbidden = client.post(f"/tasks/{task_id}/comments", headers=stranger, json={"body": "No"})
    list_forbidden = client.get(f"/tasks/{task_id}/comments", headers=stranger)
    edit_forbidden = client.patch(f"/comments/{comment_id}", headers=stranger, json={"body": "No"})
    delete_forbidden = client.delete(f"/comments/{comment_id}", headers=stranger)
    activity_forbidden = client.get(f"/tasks/{task_id}/activity", headers=stranger)

    assert create_forbidden.status_code == 403
    assert list_forbidden.status_code == 403
    assert edit_forbidden.status_code == 403
    assert delete_forbidden.status_code == 403
    assert activity_forbidden.status_code == 403


def test_manager_can_moderate_comment_but_member_cannot_edit_others(client):
    owner = register_and_login(client, "moderatedowner", "moderatedowner@example.com")
    member = register_and_login(client, "moderatedmember", "moderatedmember@example.com")
    manager = register_and_login(client, "moderatedmanager", "moderatedmanager@example.com")
    set_role("moderatedmanager@example.com", "manager")
    task = client.post("/tasks", headers=owner, json={"title": "Moderated task"})
    task_id = task.json()["id"]
    comment = client.post(f"/tasks/{task_id}/comments", headers=owner, json={"body": "Owner note"})
    comment_id = comment.json()["id"]

    member_edit = client.patch(f"/comments/{comment_id}", headers=member, json={"body": "Member edit"})
    manager_edit = client.patch(f"/comments/{comment_id}", headers=manager, json={"body": "Manager edit"})

    assert member_edit.status_code == 403
    assert manager_edit.status_code == 200


def test_activity_is_append_only_from_api(client):
    owner = register_and_login(client, "appendowner", "appendowner@example.com")
    task = client.post("/tasks", headers=owner, json={"title": "Append-only task"})
    task_id = task.json()["id"]
    client.put(f"/tasks/{task_id}", headers=owner, json={"status": "completed", "priority": "high"})

    activity = client.get(f"/tasks/{task_id}/activity", headers=owner)
    db = SessionLocal()
    try:
        count = db.query(ActivityLog).filter(ActivityLog.task_id == task_id).count()
    finally:
        db.close()

    assert activity.status_code == 200
    assert count >= 2
    assert any(event["action"] == "task_updated" for event in activity.json())
