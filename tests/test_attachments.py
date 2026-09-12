from pathlib import Path

import pytest
from starlette.websockets import WebSocketDisconnect

from app.routes import attachments as attachment_routes
from app.services import attachment_service
from app.services.storage_service import LocalFilesystemStorage, StorageError


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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def use_storage(monkeypatch, tmp_path, max_size=1024 * 1024):
    provider = LocalFilesystemStorage(str(tmp_path), max_size)
    monkeypatch.setattr(attachment_service, "storage_provider", provider)
    monkeypatch.setattr(attachment_routes, "storage_provider", provider)
    return provider


def create_task(client, headers, title="Attachment task"):
    response = client.post("/tasks", headers=headers, json={"title": title})
    assert response.status_code == 201
    return response.json()["id"]


def test_attachment_requires_authentication(client):
    response = client.get("/tasks/1/attachments")
    assert response.status_code == 401


def test_upload_list_download_and_delete_attachment(client, monkeypatch, tmp_path):
    provider = use_storage(monkeypatch, tmp_path)
    headers = register_and_login(client, "attachmentowner", "attachmentowner@example.com")
    task_id = create_task(client, headers)

    uploaded = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("notes.txt", b"hello attachment", "text/plain")},
    )
    assert uploaded.status_code == 201
    metadata = uploaded.json()
    assert metadata["original_filename"] == "notes.txt"
    assert metadata["content_type"] == "text/plain"
    assert metadata["file_size"] == len(b"hello attachment")
    assert metadata["storage_provider"] == "local"

    listed = client.get(f"/tasks/{task_id}/attachments", headers=headers)
    downloaded = client.get(
        f"/tasks/{task_id}/attachments/{metadata['id']}",
        headers=headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert downloaded.status_code == 200
    assert downloaded.content == b"hello attachment"

    deleted = client.delete(
        f"/tasks/{task_id}/attachments/{metadata['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get(f"/tasks/{task_id}/attachments", headers=headers).json() == []
    assert not list(Path(provider.root).rglob("*"))


def test_attachment_authorization_and_idor_protection(client, monkeypatch, tmp_path):
    use_storage(monkeypatch, tmp_path)
    owner = register_and_login(client, "attachmentowner2", "attachmentowner2@example.com")
    outsider = register_and_login(client, "attachmentoutsider", "attachmentoutsider@example.com")
    task_id = create_task(client, owner, "Owner task")
    other_task_id = create_task(client, owner, "Other task")
    attachment = client.post(
        f"/tasks/{task_id}/attachments",
        headers=owner,
        files={"file": ("owner.txt", b"private", "text/plain")},
    ).json()

    assert client.get(f"/tasks/{task_id}/attachments", headers=outsider).status_code == 403
    assert client.get(f"/tasks/{task_id}/attachments/{attachment['id']}", headers=outsider).status_code == 403
    assert client.delete(f"/tasks/{task_id}/attachments/{attachment['id']}", headers=outsider).status_code == 403
    assert client.get(f"/tasks/{other_task_id}/attachments/{attachment['id']}", headers=owner).status_code == 404


@pytest.mark.parametrize(
    "filename,content_type",
    [("malware.exe", "application/octet-stream"), ("notes.txt", "application/pdf"), ("../notes.txt", "text/plain")],
)
def test_invalid_attachment_is_rejected(client, monkeypatch, tmp_path, filename, content_type):
    use_storage(monkeypatch, tmp_path)
    headers = register_and_login(client, "attachmentinvalid", f"{filename.replace('.', '')}@example.com")
    task_id = create_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": (filename, b"invalid", content_type)},
    )

    assert response.status_code == 400
    assert not list(Path(tmp_path).rglob("*"))


def test_attachment_size_limit_is_enforced(client, monkeypatch, tmp_path):
    use_storage(monkeypatch, tmp_path, max_size=4)
    headers = register_and_login(client, "attachmentsize", "attachmentsize@example.com")
    task_id = create_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("large.txt", b"too large", "text/plain")},
    )

    assert response.status_code == 503
    assert not list(Path(tmp_path).rglob("*"))


def test_storage_failure_attempts_cleanup(client, monkeypatch, tmp_path):
    class FailingStorage(LocalFilesystemStorage):
        def __init__(self, root):
            super().__init__(root, 1024)
            self.deleted = []

        def store(self, stream, key):
            super().store(stream, key)
            raise StorageError("simulated storage failure")

        def delete(self, key):
            self.deleted.append(key)
            super().delete(key)

    provider = FailingStorage(str(tmp_path))
    monkeypatch.setattr(attachment_service, "storage_provider", provider)
    monkeypatch.setattr(attachment_routes, "storage_provider", provider)
    headers = register_and_login(client, "attachmentfailure", "attachmentfailure@example.com")
    task_id = create_task(client, headers)

    response = client.post(
        f"/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("failure.txt", b"cleanup", "text/plain")},
    )

    assert response.status_code == 503
    assert provider.deleted
    assert not list(Path(tmp_path).rglob("*"))