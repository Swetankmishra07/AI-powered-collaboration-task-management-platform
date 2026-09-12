from app.database.database import SessionLocal
from app.database.models import User


def register_and_login(client, username, email):
    registration = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": "StrongPassword123"},
    )
    assert registration.status_code == 201
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


def set_global_role(email, role):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one()
        user.role = role
        db.commit()
    finally:
        db.close()


def create_project_context(client):
    owner = register_and_login(client, "taskowner", "taskowner@example.com")
    member = register_and_login(client, "taskmember", "taskmember@example.com")
    outsider = register_and_login(client, "taskoutsider", "taskoutsider@example.com")
    team = client.post("/teams", headers=owner, json={"name": "Task Team"})
    team_id = team.json()["id"]
    member_id = user_id_for("taskmember@example.com")
    assert client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": member_id, "role": "member"},
    ).status_code == 201
    project = client.post(
        "/projects",
        headers=owner,
        json={"team_id": team_id, "name": "Task Project"},
    )
    project_id = project.json()["id"]
    assert client.post(
        f"/projects/{project_id}/members",
        headers=owner,
        json={"user_id": member_id, "role": "member"},
    ).status_code == 201
    return owner, member, outsider, project_id


def test_project_linked_task_scope(client):
    owner, member, outsider, project_id = create_project_context(client)

    created = client.post(
        "/tasks",
        headers=member,
        json={"title": "Project task", "project_id": project_id, "status": "todo"},
    )
    task_id = created.json()["id"]
    outsider_create = client.post(
        "/tasks",
        headers=outsider,
        json={"title": "Unauthorized project task", "project_id": project_id},
    )
    member_get = client.get(f"/tasks/{task_id}", headers=member)
    outsider_get = client.get(f"/tasks/{task_id}", headers=outsider)

    assert created.status_code == 201
    assert created.json()["project_id"] == project_id
    assert outsider_create.status_code == 403
    assert member_get.status_code == 200
    assert outsider_get.status_code == 403


def test_assignment_and_reassignment_require_project_manager(client):
    owner, member, outsider, project_id = create_project_context(client)
    manager = register_and_login(client, "taskmanager", "taskmanager@example.com")
    manager_id = user_id_for("taskmanager@example.com")
    team_id = client.get("/teams", headers=owner).json()[0]["id"]
    assert client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": manager_id, "role": "manager"},
    ).status_code == 201
    assert client.post(
        f"/projects/{project_id}/members",
        headers=manager,
        json={"user_id": manager_id, "role": "manager"},
    ).status_code == 201
    task = client.post(
        "/tasks",
        headers=owner,
        json={"title": "Assignable task", "project_id": project_id},
    )
    task_id = task.json()["id"]
    member_id = user_id_for("taskmember@example.com")

    assigned = client.put(
        f"/tasks/{task_id}",
        headers=manager,
        json={"assignee_id": member_id},
    )
    forbidden_reassignment = client.put(
        f"/tasks/{task_id}",
        headers=member,
        json={"assignee_id": user_id_for("taskowner@example.com")},
    )

    assert assigned.status_code == 200
    assert assigned.json()["assignee_id"] == member_id
    assert forbidden_reassignment.status_code == 403


def test_task_filters_pagination_sorting_search_and_deadlines(client):
    headers = register_and_login(client, "queryuser", "queryuser@example.com")
    tasks = [
        {"title": "Alpha payment", "status": "todo", "priority": "low", "deadline": "2026-01-10T12:00:00Z"},
        {"title": "Beta payment", "status": "blocked", "priority": "critical", "deadline": "2026-02-10T12:00:00Z"},
        {"title": "Gamma docs", "status": "completed", "priority": "high", "deadline": "2026-03-10T12:00:00Z"},
        {"title": "Delta payment", "status": "blocked", "priority": "critical", "deadline": "2026-04-10T12:00:00Z"},
    ]
    for task in tasks:
        assert client.post("/tasks", headers=headers, json=task).status_code == 201

    blocked = client.get("/tasks?status=blocked", headers=headers).json()
    critical = client.get("/tasks?priority=critical", headers=headers).json()
    paged = client.get("/tasks?limit=2&offset=1&sort_by=title&sort_order=asc", headers=headers).json()
    searched = client.get("/tasks?search=payment", headers=headers).json()
    deadline_filtered = client.get("/tasks?deadline_before=2026-03-01T00:00:00Z", headers=headers).json()

    assert len(blocked) == 2
    assert all(task["status"] == "blocked" for task in blocked)
    assert len(critical) == 2
    assert len(paged) == 2
    assert [task["title"] for task in paged] == ["Beta payment", "Delta payment"]
    assert len(searched) == 3
    assert len(deadline_filtered) == 2


def test_admin_can_access_project_task_without_membership(client):
    owner, member, outsider, project_id = create_project_context(client)
    admin = register_and_login(client, "taskadmin", "taskadmin@example.com")
    set_global_role("taskadmin@example.com", "admin")
    task = client.post(
        "/tasks",
        headers=owner,
        json={"title": "Admin visible task", "project_id": project_id},
    )

    response = client.get(f"/tasks/{task.json()['id']}", headers=admin)

    assert response.status_code == 200
