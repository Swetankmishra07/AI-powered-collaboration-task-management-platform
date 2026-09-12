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


def test_team_creation_membership_and_scope(client):
    owner = register_and_login(client, "teamowner", "teamowner@example.com")
    member = register_and_login(client, "teammember", "teammember@example.com")
    outsider = register_and_login(client, "outsider", "outsider@example.com")

    team = client.post(
        "/teams",
        headers=owner,
        json={"name": "Product Team", "description": "Product delivery"},
    )
    team_id = team.json()["id"]
    member_id = user_id_for("teammember@example.com")

    membership = client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": member_id, "role": "member"},
    )
    member_view = client.get(f"/teams/{team_id}", headers=member)
    outsider_view = client.get(f"/teams/{team_id}", headers=outsider)
    member_update = client.patch(
        f"/teams/{team_id}",
        headers=member,
        json={"name": "Unauthorized Rename"},
    )

    assert team.status_code == 201
    assert membership.status_code == 201
    assert member_view.status_code == 200
    assert outsider_view.status_code == 403
    assert member_update.status_code == 403


def test_team_manager_can_create_project_and_manage_members(client):
    owner = register_and_login(client, "projectowner", "projectowner@example.com")
    manager = register_and_login(client, "teammanager", "teammanager@example.com")
    project_member = register_and_login(client, "projectmember", "projectmember@example.com")

    team = client.post("/teams", headers=owner, json={"name": "Platform Team"})
    team_id = team.json()["id"]
    manager_id = user_id_for("teammanager@example.com")
    project_member_id = user_id_for("projectmember@example.com")

    manager_membership = client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": manager_id, "role": "manager"},
    )
    team_member_membership = client.post(
        f"/teams/{team_id}/members",
        headers=owner,
        json={"user_id": project_member_id, "role": "member"},
    )
    project = client.post(
        "/projects",
        headers=manager,
        json={"team_id": team_id, "name": "Payments"},
    )
    project_id = project.json()["id"]
    membership = client.post(
        f"/projects/{project_id}/members",
        headers=manager,
        json={"user_id": project_member_id, "role": "member"},
    )
    member_view = client.get(f"/projects/{project_id}", headers=project_member)
    manager_update = client.patch(
        f"/projects/{project_id}",
        headers=manager,
        json={"description": "Managed by the team manager"},
    )

    assert manager_membership.status_code == 201
    assert team_member_membership.status_code == 201
    assert project.status_code == 201
    assert membership.status_code == 201
    assert member_view.status_code == 200
    assert manager_update.status_code == 200


def test_project_requires_team_membership_and_scope(client):
    owner = register_and_login(client, "scopeowner", "scopeowner@example.com")
    outsider = register_and_login(client, "scopeoutsider", "scopeoutsider@example.com")

    team = client.post("/teams", headers=owner, json={"name": "Scoped Team"})
    team_id = team.json()["id"]
    project = client.post(
        "/projects",
        headers=owner,
        json={"team_id": team_id, "name": "Private Project"},
    )
    project_id = project.json()["id"]

    outsider_project = client.get(f"/projects/{project_id}", headers=outsider)
    outsider_list = client.get("/projects", headers=outsider)
    outsider_create = client.post(
        "/projects",
        headers=outsider,
        json={"team_id": team_id, "name": "Unauthorized Project"},
    )

    assert outsider_project.status_code == 403
    assert outsider_list.status_code == 200
    assert outsider_list.json() == []
    assert outsider_create.status_code == 403


def test_admin_can_access_and_manage_any_team_scope(client):
    owner = register_and_login(client, "adminscopeowner", "adminscopeowner@example.com")
    admin = register_and_login(client, "scopeadmin", "scopeadmin@example.com")
    set_global_role("scopeadmin@example.com", "admin")

    team = client.post("/teams", headers=owner, json={"name": "Admin Scope Team"})
    team_id = team.json()["id"]
    project = client.post(
        "/projects",
        headers=owner,
        json={"team_id": team_id, "name": "Admin Scope Project"},
    )
    project_id = project.json()["id"]

    team_view = client.get(f"/teams/{team_id}", headers=admin)
    project_view = client.get(f"/projects/{project_id}", headers=admin)
    team_update = client.patch(
        f"/teams/{team_id}",
        headers=admin,
        json={"description": "Admin update"},
    )

    assert team_view.status_code == 200
    assert project_view.status_code == 200
    assert team_update.status_code == 200


def test_unauthenticated_users_cannot_access_collaboration_endpoints(client):
    assert client.get("/teams").status_code == 401
    assert client.get("/projects").status_code == 401
