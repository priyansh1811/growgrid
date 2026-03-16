"""Tavily search API wrapper.

Provides a thin abstraction with a mockable interface for testing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from growgrid_core.config import TAVILY_API_KEY

logger = logging.getLogger(__name__)


class BaseTavilyClient(ABC):
    """Abstract Tavily search interface."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Execute a search query. Returns list of result dicts with keys:
        title, url, content (snippet).
        """


class TavilyClient(BaseTavilyClient):
    """Real Tavily client backed by tavily-python SDK."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or TAVILY_API_KEY
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from tavily import TavilyClient as _TC
                self._client = _TC(api_key=self._api_key)
            except ImportError:
                raise ImportError("tavily-python package required. pip install tavily-python")
        return self._client

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        try:
            client = self._get_client()
            response = client.search(query=query, max_results=max_results)
            results = response.get("results", [])
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Tavily search failed for '%s': %s", query, e)
            return []


class MockTavilyClient(BaseTavilyClient):
    """Mock Tavily client for testing — returns canned results."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results or [
            {
                "title": "Mock farming article",
                "url": "https://example.com/farming",
                "content": "This crop is suitable for the given region and conditions.",
            }
        ]
        self.call_log: list[str] = []

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.call_log.append(query)
        return self._results[:max_results]


def get_tavily_client(mock: BaseTavilyClient | None = None) -> BaseTavilyClient:
    """Factory: returns mock if provided, else real Tavily client."""
    if mock is not None:
        return mock
    return TavilyClient()
