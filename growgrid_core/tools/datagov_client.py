"""data.gov.in Mandi Price API client.

Fetches daily commodity prices from AGMARKNET via the data.gov.in open-data API.
Provides structured price data (Min_Price, Max_Price, Modal_Price) without
requiring LLM extraction.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from growgrid_core.config import (
    DATAGOV_API_KEY,
    DATAGOV_BASE_URL,
    DATAGOV_MANDI_RESOURCE_ID,
)

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class BaseDataGovMandiClient(ABC):
    """Abstract data.gov.in mandi price interface."""

    @abstractmethod
    def fetch_commodity_prices(
        self, commodity: str, state: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch mandi price records for a commodity in a state.

        Returns list of dicts with keys:
        State, District, Market, Commodity, Variety, Grade,
        Arrival_Date, Min_Price, Max_Price, Modal_Price.
        """


class DataGovMandiClient(BaseDataGovMandiClient):
    """Real data.gov.in client using urllib (no extra dependencies)."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or DATAGOV_API_KEY

    def fetch_commodity_prices(
        self, commodity: str, state: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({
            "api-key": self._api_key,
            "format": "json",
            "limit": limit,
            "filters[commodity]": commodity,
            "filters[state.keyword]": state,
        })
        url = f"{DATAGOV_BASE_URL}/{DATAGOV_MANDI_RESOURCE_ID}?{params}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            records = data.get("records", [])
            if not isinstance(records, list):
                return []
            return records
        except Exception as e:
            logger.warning(
                "data.gov.in API call failed for %s/%s: %s", commodity, state, e
            )
            return []


class MockDataGovMandiClient(BaseDataGovMandiClient):
    """Mock client for testing — returns canned records."""

    def __init__(self, records: list[dict[str, Any]] | None = None) -> None:
        self._records = records or []
        self.call_log: list[tuple[str, str]] = []

    def fetch_commodity_prices(
        self, commodity: str, state: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        self.call_log.append((commodity, state))
        return self._records[:limit]


def get_datagov_client(
    mock: BaseDataGovMandiClient | None = None,
) -> BaseDataGovMandiClient:
    """Factory: returns mock if provided, else real data.gov.in client."""
    if mock is not None:
        return mock
    return DataGovMandiClient()
