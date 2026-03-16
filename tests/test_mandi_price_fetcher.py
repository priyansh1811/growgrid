"""Tests for the mandi price fetcher module."""

from __future__ import annotations

from datetime import date, timedelta

from growgrid_core.agents.utils.mandi_price_fetcher import (
    MandiPriceResult,
    _aggregate_datagov_records,
    fetch_mandi_prices,
    merge_prices,
)
from growgrid_core.tools.datagov_client import MockDataGovMandiClient
from growgrid_core.tools.llm_client import MockLLMClient
from growgrid_core.tools.tavily_client import MockTavilyClient
from growgrid_core.tools.tool_cache import ToolCache


# ── fetch_mandi_prices: data.gov.in primary path ──────────────────────


def test_datagov_primary_success():
    """data.gov.in returns records → MandiPriceResult with aggregated prices."""
    today = date.today().strftime("%d/%m/%Y")
    datagov = MockDataGovMandiClient(records=[
        {
            "State": "Maharashtra",
            "Market": "Pune",
            "Commodity": "Wheat",
            "Arrival_Date": today,
            "Min_Price": "2100",
            "Max_Price": "2500",
            "Modal_Price": "2300",
        },
        {
            "State": "Maharashtra",
            "Market": "Nagpur",
            "Commodity": "Wheat",
            "Arrival_Date": today,
            "Min_Price": "2000",
            "Max_Price": "2600",
            "Modal_Price": "2350",
        },
    ])

    result = fetch_mandi_prices(
        tavily=None,
        llm_client=None,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
        datagov_client=datagov,
    )

    assert result.price_min == 2000  # min across markets
    assert result.price_max == 2600  # max across markets
    assert result.source == "data.gov.in"
    assert result.confidence == "HIGH"
    assert len(datagov.call_log) == 1


def test_datagov_empty_falls_back_to_tavily():
    """data.gov.in returns no records → falls back to Tavily+LLM."""
    datagov = MockDataGovMandiClient(records=[])
    tavily = MockTavilyClient(results=[
        {
            "title": "Wheat Price",
            "url": "https://example.com",
            "content": "Wheat 2100-2500",
        }
    ])
    llm = MockLLMClient(responses=[
        {
            "price_min": 2100,
            "price_max": 2500,
            "source": "example.com",
            "confidence": "MED",
        }
    ])

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
        datagov_client=datagov,
    )

    assert result.price_min == 2100
    assert result.price_max == 2500
    assert result.source == "example.com"
    assert len(datagov.call_log) == 1
    assert len(tavily.call_log) == 1


def test_datagov_no_mapping_falls_back_to_tavily():
    """Crop has no commodity mapping → skips data.gov.in, uses Tavily."""
    datagov = MockDataGovMandiClient(records=[
        {"Min_Price": "1000", "Max_Price": "2000", "Arrival_Date": "15/03/2026"},
    ])
    tavily = MockTavilyClient(results=[
        {"title": "Test", "url": "https://example.com", "content": "Price 500-600"}
    ])
    llm = MockLLMClient(responses=[
        {"price_min": 500, "price_max": 600, "source": "test", "confidence": "MED"}
    ])

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Quinoa",  # Not in commodity mapping
        state="Maharashtra",
        datagov_client=datagov,
    )

    # data.gov.in should NOT have been called (no mapping)
    assert len(datagov.call_log) == 0
    # Tavily should have been called as fallback
    assert len(tavily.call_log) == 1
    assert result.price_min == 500


def test_datagov_cache_hit_skips_both(tmp_path):
    """Cache hit → skips both data.gov.in and Tavily."""
    cache = ToolCache(db_path=tmp_path / "test_cache.db")
    today = date.today().strftime("%d/%m/%Y")
    datagov = MockDataGovMandiClient(records=[
        {"Min_Price": "2100", "Max_Price": "2500", "Arrival_Date": today,
         "State": "Maharashtra", "Commodity": "Wheat"},
    ])
    tavily = MockTavilyClient(results=[])

    # First call — hits data.gov.in
    r1 = fetch_mandi_prices(
        tavily=tavily, llm_client=None, cache=cache,
        crop_name="Wheat", state="Maharashtra", datagov_client=datagov,
    )
    assert r1.source == "data.gov.in"
    assert len(datagov.call_log) == 1

    # Second call — should use cache
    r2 = fetch_mandi_prices(
        tavily=tavily, llm_client=None, cache=cache,
        crop_name="Wheat", state="Maharashtra", datagov_client=datagov,
    )
    assert r2.price_min == 2100
    assert len(datagov.call_log) == 1  # no additional call
    assert len(tavily.call_log) == 0


def test_both_fail_returns_empty():
    """Both data.gov.in and Tavily return nothing → empty result."""
    datagov = MockDataGovMandiClient(records=[])

    result = fetch_mandi_prices(
        tavily=None, llm_client=None, cache=None,
        crop_name="Wheat", state="Maharashtra", datagov_client=datagov,
    )

    assert result.price_min is None
    assert result.confidence == "LOW"
    assert result.source == "not_found"


# ── _aggregate_datagov_records tests ──────────────────────────────────


def test_aggregate_recent_records_high_confidence():
    """Records from today → HIGH confidence."""
    today = date.today().strftime("%d/%m/%Y")
    records = [
        {"Min_Price": "2000", "Max_Price": "2400", "Arrival_Date": today},
        {"Min_Price": "2100", "Max_Price": "2600", "Arrival_Date": today},
    ]

    result = _aggregate_datagov_records(records)

    assert result is not None
    assert result.price_min == 2000
    assert result.price_max == 2600
    assert result.confidence == "HIGH"


def test_aggregate_old_records_low_confidence():
    """Records older than 30 days → LOW confidence."""
    old_date = (date.today() - timedelta(days=45)).strftime("%d/%m/%Y")
    records = [
        {"Min_Price": "1500", "Max_Price": "1800", "Arrival_Date": old_date},
    ]

    result = _aggregate_datagov_records(records)

    assert result is not None
    assert result.confidence == "LOW"


def test_aggregate_mid_age_records_med_confidence():
    """Records 8-30 days old → MED confidence."""
    mid_date = (date.today() - timedelta(days=15)).strftime("%d/%m/%Y")
    records = [
        {"Min_Price": "3000", "Max_Price": "3500", "Arrival_Date": mid_date},
    ]

    result = _aggregate_datagov_records(records)

    assert result is not None
    assert result.confidence == "MED"


def test_aggregate_empty_records_returns_none():
    """No valid price data → None."""
    assert _aggregate_datagov_records([]) is None
    assert _aggregate_datagov_records([{"Min_Price": "0", "Max_Price": "0"}]) is None


def test_aggregate_swaps_inverted_prices():
    """If min > max after aggregation, they get swapped."""
    today = date.today().strftime("%d/%m/%Y")
    # Single record where only Max_Price field has a value, Min_Price is higher
    # across records
    records = [
        {"Min_Price": "3000", "Max_Price": "2000", "Arrival_Date": today},
    ]

    result = _aggregate_datagov_records(records)

    assert result is not None
    assert result.price_min == 2000
    assert result.price_max == 3000


# ── fetch_mandi_prices: Tavily fallback path (existing tests) ─────────


def test_fetch_returns_prices_from_tavily_and_llm():
    """Valid Tavily results + LLM extraction → MandiPriceResult with prices."""
    tavily = MockTavilyClient(
        results=[
            {
                "title": "Wheat Mandi Price Maharashtra 2025",
                "url": "https://agmarknet.example.com/wheat",
                "content": "Wheat prices in Maharashtra range from 2100 to 2500 INR/quintal.",
            }
        ]
    )
    llm = MockLLMClient(
        responses=[
            {
                "price_min": 2100,
                "price_max": 2500,
                "source": "agmarknet.example.com",
                "confidence": "HIGH",
            }
        ]
    )

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
    )

    assert isinstance(result, MandiPriceResult)
    assert result.price_min == 2100
    assert result.price_max == 2500
    assert result.confidence == "HIGH"
    assert result.source == "agmarknet.example.com"
    assert len(tavily.call_log) == 1


def test_fetch_returns_empty_when_tavily_is_none():
    """No Tavily client → graceful fallback."""
    result = fetch_mandi_prices(
        tavily=None,
        llm_client=None,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
    )

    assert result.price_min is None
    assert result.price_max is None
    assert result.confidence == "LOW"
    assert result.source == "not_found"


def test_fetch_returns_empty_when_tavily_returns_no_results():
    """Tavily returns empty results → fallback."""
    tavily = MockTavilyClient(results=[])
    llm = MockLLMClient(responses=[])

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
    )

    assert result.price_min is None
    assert result.price_max is None
    assert result.confidence == "LOW"


def test_fetch_uses_cache_on_second_call(tmp_path):
    """Second call for same crop/state uses cache, doesn't call Tavily again."""
    cache = ToolCache(db_path=tmp_path / "test_cache.db")
    tavily = MockTavilyClient(
        results=[
            {
                "title": "Rice Price",
                "url": "https://example.com",
                "content": "Rice 1800-2200 INR/quintal",
            }
        ]
    )
    llm = MockLLMClient(
        responses=[
            {
                "price_min": 1800,
                "price_max": 2200,
                "source": "example.com",
                "confidence": "MED",
            }
        ]
    )

    # First call — hits Tavily
    r1 = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=cache,
        crop_name="Rice",
        state="Punjab",
    )
    assert r1.price_min == 1800
    assert len(tavily.call_log) == 1

    # Second call — should use cache
    r2 = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=cache,
        crop_name="Rice",
        state="Punjab",
    )
    assert r2.price_min == 1800
    assert len(tavily.call_log) == 1  # no additional Tavily call


def test_fetch_handles_invalid_llm_response():
    """LLM returns non-dict → graceful fallback."""
    tavily = MockTavilyClient(
        results=[
            {
                "title": "Test",
                "url": "https://example.com",
                "content": "Some content",
            }
        ]
    )
    llm = MockLLMClient(responses=["not a dict"])

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
    )

    assert result.price_min is None
    assert result.confidence == "LOW"


def test_fetch_swaps_min_max_when_inverted():
    """LLM returns min > max → prices are swapped."""
    tavily = MockTavilyClient(
        results=[
            {
                "title": "Test",
                "url": "https://example.com",
                "content": "Prices 2500-2100",
            }
        ]
    )
    llm = MockLLMClient(
        responses=[
            {
                "price_min": 2500,
                "price_max": 2100,
                "source": "test",
                "confidence": "MED",
            }
        ]
    )

    result = fetch_mandi_prices(
        tavily=tavily,
        llm_client=llm,
        cache=None,
        crop_name="Wheat",
        state="Maharashtra",
    )

    assert result.price_min == 2100
    assert result.price_max == 2500


# ── merge_prices tests ──────────────────────────────────────────────────


def test_merge_uses_mandi_when_within_range():
    """Mandi price within ±50% of DB → use mandi."""
    db_bands = {
        "low_price_per_unit": 1800,
        "base_price_per_unit": 2200,
        "high_price_per_unit": 2600,
    }
    mandi = MandiPriceResult(
        price_min=2000,
        price_max=2400,
        source="agmarknet",
        confidence="HIGH",
        fetch_date="2025-01-15",
    )

    merged = merge_prices(db_bands, mandi)
    assert merged["source"] == "live_fetch"
    assert merged["price_min"] == 2000
    assert merged["price_max"] == 2400
    assert merged["confidence"] == "HIGH"


def test_merge_uses_db_when_mandi_deviates():
    """Mandi price deviates >50% from DB → use DB."""
    db_bands = {
        "low_price_per_unit": 1800,
        "base_price_per_unit": 2200,
        "high_price_per_unit": 2600,
    }
    mandi = MandiPriceResult(
        price_min=5000,
        price_max=6000,
        source="agmarknet",
        confidence="HIGH",
        fetch_date="2025-01-15",
    )

    merged = merge_prices(db_bands, mandi)
    assert merged["source"] == "database"
    assert merged["price_min"] == 1800
    assert merged["price_max"] == 2600


def test_merge_uses_db_when_mandi_is_low_confidence():
    """Mandi with LOW confidence → use DB regardless."""
    db_bands = {
        "low_price_per_unit": 1800,
        "base_price_per_unit": 2200,
        "high_price_per_unit": 2600,
    }
    mandi = MandiPriceResult(
        price_min=2000,
        price_max=2400,
        source="not_found",
        confidence="LOW",
        fetch_date="2025-01-15",
    )

    merged = merge_prices(db_bands, mandi)
    assert merged["source"] == "database"


def test_merge_uses_mandi_when_db_is_empty():
    """No DB price data → use mandi if available."""
    mandi = MandiPriceResult(
        price_min=3000,
        price_max=4000,
        source="agmarknet",
        confidence="MED",
        fetch_date="2025-01-15",
    )

    merged = merge_prices(None, mandi)
    assert merged["source"] == "live_fetch"
    assert merged["price_min"] == 3000


def test_merge_fallback_when_both_empty():
    """No DB and no mandi → fallback zeros."""
    mandi = MandiPriceResult(
        price_min=None,
        price_max=None,
        source="not_found",
        confidence="LOW",
        fetch_date="2025-01-15",
    )

    merged = merge_prices(None, mandi)
    assert merged["source"] == "fallback"
    assert merged["price_min"] == 0
    assert merged["confidence"] == "LOW"
