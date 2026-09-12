import jwt

from app.core.config import settings


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
    return response.json()


def test_security_headers_are_present(client):
    response = client.get("/")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_jwt_wrong_audience_and_type_are_rejected(client):
    tokens = register_and_login(client, "claimuser", "claimuser@example.com")
    valid_payload = jwt.decode(
        tokens["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_aud": False},
    )
    wrong_audience = jwt.encode(
        {**valid_payload, "aud": "wrong-client"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    wrong_type = jwt.encode(
        {**valid_payload, "typ": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    wrong_audience_response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {wrong_audience}"},
    )
    wrong_type_response = client.get(
        "/tasks",
        headers={"Authorization": f"Bearer {wrong_type}"},
    )

    assert wrong_audience_response.status_code == 401
    assert wrong_type_response.status_code == 401


def test_refresh_reuse_failure_is_generic(client):
    tokens = register_and_login(client, "refreshsecurity", "refreshsecurity@example.com")
    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert first.status_code == 200
    assert reused.status_code == 401
    assert reused.json()["error"]["message"] == "Invalid refresh token"


def test_attachment_filename_header_controls_are_rejected(client, monkeypatch, tmp_path):
    from app.routes import attachments as attachment_routes
    from app.services import attachment_service
    from app.services.storage_service import LocalFilesystemStorage

    provider = LocalFilesystemStorage(str(tmp_path), 1024)
    monkeypatch.setattr(attachment_service, "storage_provider", provider)
    monkeypatch.setattr(attachment_routes, "storage_provider", provider)
    headers = register_and_login(client, "filenameuser", "filenameuser@example.com")
    task = client.post("/tasks", headers={"Authorization": f"Bearer {headers['access_token']}"}, json={"title": "File task"}).json()
    auth = {"Authorization": f"Bearer {headers['access_token']}"}

    response = client.post(
        f"/tasks/{task['id']}/attachments",
        headers=auth,
        files={"file": ("safe.txt\r\nX-Leak: yes", b"data", "text/plain")},
    )

    assert response.status_code == 400