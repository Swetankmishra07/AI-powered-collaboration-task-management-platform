from app.routes import ai as ai_routes
from app.schemas.ai import AITaskDraft
from app.schemas.task import TaskPriority, TaskStatus
from app.services import ai_service as ai_service_module
from app.services.ai_service import AIProvider, AIProviderError


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


class FakeProvider(AIProvider):
    def __init__(self):
        self.contexts = []

    def create_task(self, prompt):
        self.contexts.append({"operation": "create", "prompt": prompt})
        return AITaskDraft(
            title="Prepare launch checklist",
            description="Create and review the launch checklist.",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
        )

    def summarize_task(self, context):
        self.contexts.append({"operation": "summary", "context": context})
        return "The task is active and needs a launch checklist before release."

    def suggest_priority(self, context):
        self.contexts.append({"operation": "priority", "context": context})
        return TaskPriority.CRITICAL, "The deadline and release dependency make this urgent."


class FailingProvider(FakeProvider):
    def summarize_task(self, context):
        raise AIProviderError("provider unavailable")


def test_ai_requires_authentication(client):
    response = client.post("/ai/tasks/from-text", json={"prompt": "Prepare a launch checklist"})
    assert response.status_code == 401


def test_ai_task_creation_uses_existing_task_service(client, monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr(ai_routes.ai_service, "provider", fake)
    headers = register_and_login(client, "aitaskuser", "aitaskuser@example.com")

    response = client.post(
        "/ai/tasks/from-text",
        headers=headers,
        json={"prompt": "We need a launch checklist before release."},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Prepare launch checklist"
    assert response.json()["priority"] == "high"
    assert fake.contexts[0]["prompt"].startswith("We need")


def test_ai_summary_and_priority_respect_task_authorization(client, monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr(ai_routes.ai_service, "provider", fake)
    owner = register_and_login(client, "aisummaryowner", "aisummaryowner@example.com")
    outsider = register_and_login(client, "aisummaryoutsider", "aisummaryoutsider@example.com")
    task = client.post(
        "/tasks",
        headers=owner,
        json={"title": "Release task", "description": "Ship the release."},
    ).json()

    summary = client.post(f"/ai/tasks/{task['id']}/summary", headers=owner)
    suggestion = client.post(f"/ai/tasks/{task['id']}/priority-suggestion", headers=owner)
    forbidden = client.post(f"/ai/tasks/{task['id']}/summary", headers=outsider)

    assert summary.status_code == 200
    assert "launch checklist" in summary.json()["summary"]
    assert suggestion.status_code == 200
    assert suggestion.json() == {
        "priority": "critical",
        "explanation": "The deadline and release dependency make this urgent.",
    }
    assert forbidden.status_code == 403
    assert [item["operation"] for item in fake.contexts] == ["summary", "priority"]


def test_priority_suggestion_does_not_change_stored_priority(client, monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr(ai_routes.ai_service, "provider", fake)
    headers = register_and_login(client, "aipriorityuser", "aipriorityuser@example.com")
    task = client.post(
        "/tasks",
        headers=headers,
        json={"title": "Priority task", "priority": "low"},
    ).json()

    response = client.post(f"/ai/tasks/{task['id']}/priority-suggestion", headers=headers)
    stored = client.get(f"/tasks/{task['id']}", headers=headers)

    assert response.status_code == 200
    assert stored.json()["priority"] == "low"


def test_provider_failure_returns_gateway_error(client, monkeypatch):
    monkeypatch.setattr(ai_routes.ai_service, "provider", FailingProvider())
    headers = register_and_login(client, "aifailureuser", "aifailureuser@example.com")
    task = client.post("/tasks", headers=headers, json={"title": "Failure task"}).json()

    response = client.post(f"/ai/tasks/{task['id']}/summary", headers=headers)

    assert response.status_code == 502
    assert "provider" in response.json()["error"]["message"].lower()


def test_missing_ai_configuration_is_graceful(client, monkeypatch):
    monkeypatch.setattr(ai_routes.ai_service, "provider", None)
    monkeypatch.setattr(ai_service_module.settings, "AI_ENABLED", False)
    headers = register_and_login(client, "aimissinguser", "aimissinguser@example.com")

    response = client.post("/ai/tasks/from-text", headers=headers, json={"prompt": "Draft a task"})

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "AI features are not configured."