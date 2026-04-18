"""LLM client abstraction — swappable backend (OpenAI default).

Usage:
    client = get_llm_client()
    result = client.complete(system_prompt, user_prompt)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from growgrid_core.config import LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE, OPENAI_API_KEY

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Abstract LLM backend."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
    ) -> dict[str, Any]:
        """Send prompts and return parsed JSON dict."""

    @abstractmethod
    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send prompts and return raw text response."""


class OpenAILLMClient(BaseLLMClient):
    """OpenAI-backed LLM client using gpt-4.1-mini by default."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or OPENAI_API_KEY
        self._model = model or LLM_MODEL
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package required. pip install openai")
        return self._client

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
    ) -> dict[str, Any]:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": LLM_TEMPERATURE,
            "max_completion_tokens": LLM_MAX_TOKENS,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON: %s", text[:200])
            return {"raw_text": text}

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=LLM_TEMPERATURE,
            max_completion_tokens=LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content or ""


class MockLLMClient(BaseLLMClient):
    """In-memory mock for testing — returns canned responses."""

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self._responses = list(responses) if responses else []
        self._call_count = 0

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: str = "json",
    ) -> dict[str, Any]:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
        else:
            resp = {"status": "mock_default"}
        self._call_count += 1
        return resp

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        result = self.complete(system_prompt, user_prompt, response_format="text")
        return result.get("raw_text", json.dumps(result))


def get_llm_client(mock: BaseLLMClient | None = None) -> BaseLLMClient:
    """Factory: returns mock if provided, else real OpenAI client."""
    if mock is not None:
        return mock
    return OpenAILLMClient()
