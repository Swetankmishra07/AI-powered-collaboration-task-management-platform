from datetime import timedelta

from app.core.security import create_access_token


def test_user_registration_success(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser_reg",
            "email": "testuser_reg@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser_reg"
    assert data["email"] == "testuser_reg@example.com"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_user_registration_fails(client):
    # First registration
    client.post(
        "/auth/register",
        json={
            "username": "dupuser",
            "email": "dupuser@example.com",
            "password": "StrongPassword123"
        }
    )
    # Duplicate registration attempt
    response = client.post(
        "/auth/register",
        json={
            "username": "dupuser",
            "email": "dupuser@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 400


def test_user_login_success(client):
    client.post(
        "/auth/register",
        json={
            "username": "loginuser",
            "email": "loginuser@example.com",
            "password": "StrongPassword123"
        }
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "StrongPassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] > 0
    assert data["token_type"] == "bearer"


def test_login_invalid_password_fails(client):
    client.post(
        "/auth/register",
        json={
            "username": "badpassuser",
            "email": "badpassuser@example.com",
            "password": "StrongPassword123"
        }
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "badpassuser@example.com",
            "password": "WrongPassword999"
        }
    )
    assert response.status_code == 401


def test_invalid_email_and_password_have_same_auth_error(client):
    client.post(
        "/auth/register",
        json={
            "username": "enumerationuser",
            "email": "enumeration@example.com",
            "password": "StrongPassword123",
        },
    )
    wrong_password = client.post(
        "/auth/login",
        json={"email": "enumeration@example.com", "password": "WrongPassword999"},
    )
    unknown_email = client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "WrongPassword999"},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_expired_access_token_is_rejected(client):
    client.post(
        "/auth/register",
        json={
            "username": "expireduser",
            "email": "expired@example.com",
            "password": "StrongPassword123",
        },
    )
    token = create_access_token(
        {"sub": "1", "email": "expired@example.com"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get("/tasks", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token has expired"


def test_refresh_token_rotation_and_reuse_detection(client):
    client.post(
        "/auth/register",
        json={
            "username": "refreshuser",
            "email": "refresh@example.com",
            "password": "StrongPassword123",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "StrongPassword123"},
    )
    original_refresh = login.json()["refresh_token"]

    rotated = client.post("/auth/refresh", json={"refresh_token": original_refresh})

    assert rotated.status_code == 200
    rotated_refresh = rotated.json()["refresh_token"]
    assert rotated_refresh != original_refresh

    reused = client.post("/auth/refresh", json={"refresh_token": original_refresh})
    invalidated_replacement = client.post(
        "/auth/refresh", json={"refresh_token": rotated_refresh}
    )

    assert reused.status_code == 401
    assert invalidated_replacement.status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post(
        "/auth/register",
        json={
            "username": "logoutuser",
            "email": "logout@example.com",
            "password": "StrongPassword123",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "logout@example.com", "password": "StrongPassword123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert logout.status_code == 204
    assert refresh.status_code == 401


def test_valid_access_token_protects_task_endpoint(client):
    client.post(
        "/auth/register",
        json={
            "username": "protecteduser",
            "email": "protected@example.com",
            "password": "StrongPassword123",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "protected@example.com", "password": "StrongPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/tasks", headers=headers)

    assert response.status_code == 200
