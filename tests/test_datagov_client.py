"""Tests for the data.gov.in mandi price client."""

from __future__ import annotations

from growgrid_core.tools.datagov_client import (
    MockDataGovMandiClient,
    get_datagov_client,
)


def test_mock_client_returns_records():
    """MockDataGovMandiClient returns canned records and logs calls."""
    records = [
        {
            "State": "Maharashtra",
            "District": "Pune",
            "Market": "Pune",
            "Commodity": "Wheat",
            "Variety": "Lokwan",
            "Arrival_Date": "15/03/2026",
            "Min_Price": "2100",
            "Max_Price": "2500",
            "Modal_Price": "2300",
        }
    ]
    client = MockDataGovMandiClient(records=records)

    result = client.fetch_commodity_prices("Wheat", "Maharashtra")

    assert len(result) == 1
    assert result[0]["Commodity"] == "Wheat"
    assert result[0]["Min_Price"] == "2100"
    assert len(client.call_log) == 1
    assert client.call_log[0] == ("Wheat", "Maharashtra")


def test_mock_client_empty():
    """Empty mock returns []."""
    client = MockDataGovMandiClient()

    result = client.fetch_commodity_prices("Wheat", "Maharashtra")

    assert result == []
    assert len(client.call_log) == 1


def test_factory_returns_mock():
    """get_datagov_client(mock) returns the mock."""
    mock = MockDataGovMandiClient()
    client = get_datagov_client(mock=mock)
    assert client is mock
