"""Tests for the commodity name mapping module."""

from __future__ import annotations

from growgrid_core.agents.utils.commodity_mapping import resolve_commodity_name


def test_exact_match():
    """Exact crop name maps correctly."""
    assert resolve_commodity_name("Wheat") == "Wheat"
    assert resolve_commodity_name("Tomato") == "Tomato"
    assert resolve_commodity_name("Onion") == "Onion"


def test_case_insensitive():
    """Matching is case-insensitive."""
    assert resolve_commodity_name("wheat") == "Wheat"
    assert resolve_commodity_name("TOMATO") == "Tomato"
    assert resolve_commodity_name("Rice (Paddy)") == "Paddy(Dhan)(Common)"


def test_parenthetical_name():
    """Crop names with parentheses map correctly."""
    assert resolve_commodity_name("Chickpea (Gram)") == "Bengal Gram(Gram)(Whole)"
    assert resolve_commodity_name("Okra (Bhindi)") == "Bhindi(Ladies Finger)"
    assert resolve_commodity_name("Bajra (Pearl millet)") == "Bajra(Pearl Millet/Cumbu)"


def test_protected_crops():
    """Protected crop variants map to their base commodity."""
    assert resolve_commodity_name("Capsicum (Protected)") == "Capsicum"
    assert resolve_commodity_name("Tomato (Protected)") == "Tomato"
    assert resolve_commodity_name("Cucumber (Protected)") == "Cucumber(Kakadi)"


def test_no_mapping_returns_none():
    """Unknown crop returns None."""
    assert resolve_commodity_name("Quinoa") is None
    assert resolve_commodity_name("Avocado") is None
    assert resolve_commodity_name("") is None


def test_substring_match():
    """Substring matching works for partial names."""
    # "potato" is contained in "potato (seed)" mapping key
    result = resolve_commodity_name("Potato")
    assert result == "Potato"
