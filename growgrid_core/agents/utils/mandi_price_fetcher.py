"""Mandi price fetcher — live price verification via data.gov.in API and Tavily.

Primary source: data.gov.in AGMARKNET API (structured, no LLM needed).
Secondary fallback: Tavily web search + LLM extraction.
Results are cached for 24 hours.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from growgrid_core.agents.utils.commodity_mapping import resolve_commodity_name
from growgrid_core.tools.datagov_client import BaseDataGovMandiClient
from growgrid_core.tools.llm_client import BaseLLMClient
from growgrid_core.tools.tavily_client import BaseTavilyClient
from growgrid_core.tools.tool_cache import ToolCache

logger = logging.getLogger(__name__)

_CACHE_TTL_HOURS = 24

_EXTRACTION_SYSTEM_PROMPT = """\
You are a data extractor. From the search results below, extract ONLY the \
numeric price range for {crop} in {state} in INR per quintal.

Return ONLY a JSON object:
{{
  "price_min": <number or null>,
  "price_max": <number or null>,
  "source": "<source description or URL>",
  "confidence": "HIGH" | "MED" | "LOW"
}}

Rules:
- If no reliable price data is found, return price_min: null, price_max: null, source: "not_found", confidence: "LOW"
- Do NOT invent numbers — only extract from the search results
- price_min must be <= price_max
- Prices must be in INR per quintal
- HIGH confidence = exact recent mandi price data found
- MED confidence = price range found but may be dated or approximate
- LOW confidence = no reliable data found
"""


@dataclass
class MandiPriceResult:
    """Result from a mandi price lookup."""

    price_min: float | None
    price_max: float | None
    source: str
    confidence: str  # HIGH, MED, LOW
    fetch_date: str  # ISO date


def _empty_result() -> MandiPriceResult:
    return MandiPriceResult(
        price_min=None,
        price_max=None,
        source="not_found",
        confidence="LOW",
        fetch_date=date.today().isoformat(),
    )


def _aggregate_datagov_records(
    records: list[dict[str, Any]],
) -> MandiPriceResult | None:
    """Aggregate multiple data.gov.in market records into a single result.

    Returns None if no valid price data found.
    """
    min_prices: list[float] = []
    max_prices: list[float] = []
    dates: list[date] = []

    for r in records:
        try:
            min_p = float(r.get("min_price") or r.get("Min_Price") or 0)
            max_p = float(r.get("max_price") or r.get("Max_Price") or 0)
            if min_p > 0:
                min_prices.append(min_p)
            if max_p > 0:
                max_prices.append(max_p)
            arrival = r.get("arrival_date") or r.get("Arrival_Date") or ""
            if arrival:
                try:
                    dates.append(datetime.strptime(arrival, "%d/%m/%Y").date())
                except ValueError:
                    pass
        except (ValueError, TypeError):
            continue

    if not min_prices or not max_prices:
        return None

    price_min = min(min_prices)
    price_max = max(max_prices)

    if price_min > price_max:
        price_min, price_max = price_max, price_min

    # Determine confidence from data recency
    if dates:
        most_recent = max(dates)
        days_old = (date.today() - most_recent).days
        if days_old <= 7:
            confidence = "HIGH"
        elif days_old <= 30:
            confidence = "MED"
        else:
            confidence = "LOW"
        fetch_date = most_recent.isoformat()
    else:
        confidence = "MED"
        fetch_date = date.today().isoformat()

    return MandiPriceResult(
        price_min=price_min,
        price_max=price_max,
        source="data.gov.in",
        confidence=confidence,
        fetch_date=fetch_date,
    )


def _cache_and_return(
    cache: ToolCache | None, cache_key: str, result: MandiPriceResult
) -> MandiPriceResult:
    """Cache a result and return it."""
    if cache is not None:
        cache_payload = [{
            "price_min": result.price_min,
            "price_max": result.price_max,
            "source": result.source,
            "confidence": result.confidence,
            "fetch_date": result.fetch_date,
        }]
        try:
            cache.set(cache_key, cache_payload, ttl_hours=_CACHE_TTL_HOURS)
        except Exception:
            pass  # cache write failure is non-fatal
    return result


def fetch_mandi_prices(
    tavily: BaseTavilyClient | None,
    llm_client: BaseLLMClient | None,
    cache: ToolCache | None,
    crop_name: str,
    state: str,
    datagov_client: BaseDataGovMandiClient | None = None,
) -> MandiPriceResult:
    """Fetch live mandi prices for a crop in a state.

    Priority: cache → data.gov.in API → Tavily+LLM → empty fallback.

    Args:
        tavily: Tavily search client (can be None).
        llm_client: LLM client for extracting prices from search results.
        cache: Optional cache (shared with other agents).
        crop_name: Human-readable crop name (e.g., "Wheat").
        state: Indian state name (e.g., "Maharashtra").
        datagov_client: data.gov.in API client (can be None).

    Returns:
        MandiPriceResult with extracted prices or empty fallback.
    """
    cache_key = f"mandi|{crop_name.lower().strip()}|{state.lower().strip()}|v2"

    # ── 1. Check cache ────────────────────────────────────────────────
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            try:
                entry = cached[0] if isinstance(cached, list) else cached
                return MandiPriceResult(
                    price_min=entry.get("price_min"),
                    price_max=entry.get("price_max"),
                    source=entry.get("source", "cache"),
                    confidence=entry.get("confidence", "MED"),
                    fetch_date=entry.get("fetch_date", date.today().isoformat()),
                )
            except Exception:
                pass  # stale/corrupt cache, proceed with fresh fetch

    # ── 2. Try data.gov.in API (primary) ──────────────────────────────
    if datagov_client is not None:
        commodity = resolve_commodity_name(crop_name)
        if commodity is not None:
            try:
                records = datagov_client.fetch_commodity_prices(commodity, state)
                if records:
                    result = _aggregate_datagov_records(records)
                    if result is not None and result.price_min is not None:
                        logger.info(
                            "data.gov.in price for %s/%s: ₹%.0f–%.0f (%s)",
                            crop_name, state, result.price_min, result.price_max,
                            result.confidence,
                        )
                        return _cache_and_return(cache, cache_key, result)
            except Exception as e:
                logger.warning(
                    "data.gov.in fetch failed for %s/%s: %s", crop_name, state, e
                )

    # ── 3. Fallback to Tavily + LLM ──────────────────────────────────
    if tavily is None or llm_client is None:
        return _empty_result()

    query = f"{crop_name} mandi price {state} 2025 AGMARKNET"
    try:
        search_results = tavily.search(query, max_results=5)
    except Exception as e:
        logger.warning("Mandi price Tavily search failed for %s/%s: %s", crop_name, state, e)
        return _empty_result()

    if not search_results:
        return _empty_result()

    # Format search results for LLM
    snippets = "\n\n".join(
        f"Source: {r.get('title', 'N/A')}\nURL: {r.get('url', '')}\n{r.get('content', '')}"
        for r in search_results
    )

    system_prompt = _EXTRACTION_SYSTEM_PROMPT.format(crop=crop_name, state=state)
    user_prompt = f"Search results:\n\n{snippets}"

    try:
        result_dict = llm_client.complete(system_prompt, user_prompt, response_format="json")
    except Exception as e:
        logger.warning("LLM extraction failed for mandi prices %s/%s: %s", crop_name, state, e)
        return _empty_result()

    if not isinstance(result_dict, dict):
        return _empty_result()

    # Validate extracted prices
    price_min = result_dict.get("price_min")
    price_max = result_dict.get("price_max")
    source = str(result_dict.get("source", "not_found"))
    confidence = str(result_dict.get("confidence", "LOW")).upper()

    if confidence not in {"HIGH", "MED", "LOW"}:
        confidence = "LOW"

    if price_min is not None and price_max is not None:
        try:
            price_min = float(price_min)
            price_max = float(price_max)
        except (ValueError, TypeError):
            price_min, price_max = None, None

        if price_min is not None and price_max is not None:
            if price_min <= 0 or price_max <= 0:
                price_min, price_max = None, None
            elif price_min > price_max:
                price_min, price_max = price_max, price_min
    else:
        price_min, price_max = None, None
        confidence = "LOW"

    mandi_result = MandiPriceResult(
        price_min=price_min,
        price_max=price_max,
        source=source,
        confidence=confidence,
        fetch_date=date.today().isoformat(),
    )

    return _cache_and_return(cache, cache_key, mandi_result)


# Confidence-weighted blend factors: how much to shift toward live data
_BLEND_WEIGHT: dict[str, float] = {
    "HIGH": 0.75,  # 75% live, 25% DB — strong market signal
    "MED":  0.50,  # 50/50 blend — moderate confidence
    "LOW":  0.0,   # Use DB only
}


def merge_prices(
    db_price_bands: dict[str, Any] | None,
    mandi: MandiPriceResult,
) -> dict[str, Any]:
    """Merge live mandi prices with DB baseline prices using confidence-weighted blending.

    Strategy:
    - No DB data → use mandi if available.
    - No mandi or LOW confidence → use DB.
    - MED/HIGH confidence + within ±50% of DB → blend (weighted avg of DB + live).
    - Mandi deviates >50% from DB → use DB (likely bad API data).

    Blend weights: HIGH=75% live, MED=50% live, LOW=0% (DB only).

    Returns:
        Dict with: price_min, price_max, price_base,
        source ("live_fetch" | "blended_live" | "database" | "fallback"),
        confidence.
    """
    db_low = float((db_price_bands or {}).get("low_price_per_unit", 0) or 0)
    db_base = float((db_price_bands or {}).get("base_price_per_unit", 0) or 0)
    db_high = float((db_price_bands or {}).get("high_price_per_unit", 0) or 0)

    # If DB has no data, use mandi if available
    if db_low <= 0 and db_high <= 0:
        if mandi.price_min is not None and mandi.price_max is not None:
            return {
                "price_min": mandi.price_min,
                "price_max": mandi.price_max,
                "price_base": (mandi.price_min + mandi.price_max) / 2,
                "source": "live_fetch",
                "confidence": mandi.confidence,
            }
        return {
            "price_min": 0, "price_max": 0, "price_base": 0,
            "source": "fallback", "confidence": "LOW",
        }

    # If mandi data is not available or LOW confidence, use DB
    w = _BLEND_WEIGHT.get(mandi.confidence, 0.0) if (
        mandi.price_min is not None and mandi.price_max is not None
    ) else 0.0

    if w == 0.0:
        return {
            "price_min": db_low,
            "price_max": db_high,
            "price_base": db_base,
            "source": "database",
            "confidence": "MED",
        }

    # Mandi data available with MED/HIGH confidence — validate against DB range
    db_mid = (db_low + db_high) / 2
    mandi_mid = (mandi.price_min + mandi.price_max) / 2

    # Reject if mandi deviates >50% from DB midpoint (likely bad data)
    if db_mid > 0 and abs(mandi_mid - db_mid) / db_mid > 0.50:
        logger.info(
            "Mandi price for crop deviates >50%% from DB (mandi=%.0f, db=%.0f). Using DB.",
            mandi_mid, db_mid,
        )
        return {
            "price_min": db_low,
            "price_max": db_high,
            "price_base": db_base,
            "source": "database",
            "confidence": "MED",
        }

    # Confidence-weighted blend of DB and live prices
    blended_min = w * mandi.price_min + (1 - w) * db_low
    blended_max = w * mandi.price_max + (1 - w) * db_high
    blended_base = w * mandi_mid + (1 - w) * db_base

    return {
        "price_min": blended_min,
        "price_max": blended_max,
        "price_base": blended_base,
        "source": "blended_live",
        "confidence": mandi.confidence,
    }
