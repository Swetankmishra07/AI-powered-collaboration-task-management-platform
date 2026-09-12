import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from app.core.config import settings
from app.schemas.ai import AITaskDraft
from app.schemas.task import TaskPriority


logger = logging.getLogger(__name__)


class AIConfigurationError(RuntimeError):
    """Raised when AI is disabled or missing required provider settings."""


class AIProviderError(RuntimeError):
    """Raised when the configured provider cannot produce a valid result."""


class AIProvider(ABC):
    @abstractmethod
    def create_task(self, prompt: str) -> AITaskDraft:
        raise NotImplementedError

    @abstractmethod
    def summarize_task(self, context: dict[str, Any]) -> str:
        raise NotImplementedError

    @abstractmethod
    def suggest_priority(self, context: dict[str, Any]) -> tuple[TaskPriority, str]:
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    """Small adapter for providers exposing a Chat Completions-compatible API."""

    def __init__(self, api_key: str, api_url: str, model: str, timeout: float) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout

    def _complete_json(self, instruction: str, context: Any) -> dict[str, Any]:
        body = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            if content.startswith("```"):
                content = content.strip().removeprefix("```json").removesuffix("```").strip()
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError("Provider response was not an object")
            return result
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError("AI provider request failed or returned invalid data") from exc

    def create_task(self, prompt: str) -> AITaskDraft:
        result = self._complete_json(
            "Convert the user's text into a task JSON object with title, description, status, priority, deadline, assignee_id, and project_id. Use only valid task status and priority values. Keep title concise.",
            {"prompt": prompt},
        )
        try:
            return AITaskDraft.model_validate(result)
        except ValueError as exc:
            raise AIProviderError("AI provider returned an invalid task draft") from exc

    def summarize_task(self, context: dict[str, Any]) -> str:
        result = self._complete_json(
            "Summarize the authorized task context in 1-3 concise sentences. Return JSON with a summary string only.",
            context,
        )
        summary = result.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise AIProviderError("AI provider returned an invalid summary")
        return summary.strip()

    def suggest_priority(self, context: dict[str, Any]) -> tuple[TaskPriority, str]:
        result = self._complete_json(
            "Suggest a task priority based on the authorized task context. Return JSON with priority (low, medium, high, or critical) and a short explanation.",
            context,
        )
        try:
            priority = TaskPriority(result["priority"])
            explanation = result["explanation"]
            if not isinstance(explanation, str) or not explanation.strip():
                raise ValueError("Missing explanation")
            return priority, explanation.strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise AIProviderError("AI provider returned an invalid priority suggestion") from exc


def configured_provider() -> AIProvider:
    if not settings.AI_ENABLED or not settings.AI_API_KEY or not settings.AI_API_URL or not settings.AI_MODEL:
        raise AIConfigurationError("AI features are not configured")
    if settings.AI_PROVIDER != "openai_compatible":
        raise AIConfigurationError("Configured AI provider is not supported")
    return OpenAICompatibleProvider(
        api_key=settings.AI_API_KEY,
        api_url=settings.AI_API_URL,
        model=settings.AI_MODEL,
        timeout=settings.AI_REQUEST_TIMEOUT_SECONDS,
    )


class AIService:
    def __init__(self, provider: Optional[AIProvider] = None) -> None:
        self.provider = provider

    def _provider(self) -> AIProvider:
        return self.provider or configured_provider()

    def create_task(self, prompt: str) -> AITaskDraft:
        return self._provider().create_task(prompt)

    def summarize_task(self, context: dict[str, Any]) -> str:
        return self._provider().summarize_task(context)

    def suggest_priority(self, context: dict[str, Any]) -> tuple[TaskPriority, str]:
        return self._provider().suggest_priority(context)