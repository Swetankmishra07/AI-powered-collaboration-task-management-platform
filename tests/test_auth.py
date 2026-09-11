import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_user_registration_success():
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


def test_duplicate_user_registration_fails():
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


def test_user_login_success():
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
    assert data["token_type"] == "bearer"


def test_login_invalid_password_fails():
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
