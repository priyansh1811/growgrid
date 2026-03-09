"""Shared test fixtures for GrowGrid tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from growgrid_core.utils.enums import (
    Goal,
    IrrigationSource,
    LabourLevel,
    RiskLevel,
    WaterLevel,
)
from growgrid_core.utils.types import PlanRequest


@pytest.fixture
def sample_request() -> PlanRequest:
    """A typical mid-range farmer request for testing."""
    return PlanRequest(
        location="Maharashtra, Pune",
        land_area_acres=5.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=300_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=2.0,
        risk_tolerance=RiskLevel.MED,
    )


@pytest.fixture
def low_resource_request() -> PlanRequest:
    """A constrained farmer — low water, low budget, low labour."""
    return PlanRequest(
        location="Rajasthan, Jodhpur",
        land_area_acres=2.0,
        water_availability=WaterLevel.LOW,
        irrigation_source=IrrigationSource.NONE,
        budget_total_inr=40_000,
        labour_availability=LabourLevel.LOW,
        goal=Goal.STABLE_INCOME,
        time_horizon_years=1.0,
        risk_tolerance=RiskLevel.LOW,
    )


@pytest.fixture
def high_budget_request() -> PlanRequest:
    """High-budget farmer wanting fast ROI."""
    return PlanRequest(
        location="Karnataka, Bangalore Rural",
        land_area_acres=10.0,
        water_availability=WaterLevel.HIGH,
        irrigation_source=IrrigationSource.DRIP,
        budget_total_inr=2_000_000,
        labour_availability=LabourLevel.HIGH,
        goal=Goal.FAST_ROI,
        time_horizon_years=3.0,
        risk_tolerance=RiskLevel.HIGH,
    )


@pytest.fixture
def test_db(tmp_path: Path) -> sqlite3.Connection:
    """Create an in-memory test DB with minimal practice + crop data."""
    from growgrid_core.db.db_loader import create_tables

    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    _seed_test_data(conn)
    return conn


def _seed_test_data(conn: sqlite3.Connection) -> None:
    """Insert minimal test rows into practice_master and crop tables."""
    conn.executemany(
        """INSERT INTO practice_master (
            practice_code, practice_name, water_need, labour_need, risk_level,
            time_to_first_income_months_min, time_to_first_income_months_max,
            capex_min_per_acre_inr, capex_max_per_acre_inr,
            opex_min_per_acre_inr, opex_max_per_acre_inr,
            profit_potential, perishability_exposure, storage_dependency,
            suitable_when, not_suitable_when, source_id, source_tier
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                "OPEN_FIELD", "Open Field Farming", "MED", "MED", "MED",
                3, 6, 10000, 30000, 8000, 20000,
                "MED", "MED", "LOW",
                "General farming with moderate resources", "Very low water areas without irrigation",
                "SRC001", "T1",
            ),
            (
                "POLYHOUSE", "Polyhouse / Protected Cultivation", "HIGH", "HIGH", "LOW",
                2, 4, 80000, 200000, 30000, 60000,
                "VERY_HIGH", "HIGH", "MED",
                "High budget, high water, controlled environment", "Low budget or water-scarce",
                "SRC002", "T1",
            ),
            (
                "ORCHARD", "Orchard / Horticulture", "MED", "MED", "LOW",
                24, 48, 40000, 80000, 15000, 30000,
                "HIGH", "MED", "MED",
                "Long horizon, patient capital", "Short horizon under 2 years",
                "SRC003", "T1",
            ),
            (
                "RAIN_FED", "Rain-fed / Dryland Farming", "LOW", "LOW", "HIGH",
                3, 6, 5000, 15000, 3000, 10000,
                "LOW", "LOW", "LOW",
                "Low water, low budget, rainfed zone", "Irrigated zones with high water",
                "SRC004", "T1",
            ),
            (
                "INTEGRATED", "Integrated Farming System", "MED", "HIGH", "MED",
                4, 12, 25000, 60000, 12000, 30000,
                "HIGH", "MED", "MED",
                "Diversified income, moderate resources", "Very small land or very low labour",
                "SRC005", "T1",
            ),
        ],
    )

    conn.executemany(
        """INSERT INTO crop_master (
            crop_id, crop_name, category, seasons_supported,
            water_need, labour_need, risk_level,
            time_to_first_income_months_min, time_to_first_income_months_max,
            profit_potential, perishability, storage_need,
            climate_tags, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            ("TOMATO", "Tomato", "Vegetable", "KHARIF,RABI",
             "MED", "MED", "MED", 3, 5, "HIGH", "HIGH", "NO",
             "tropical,subtropical", "Popular high-value vegetable"),
            ("WHEAT", "Wheat", "Cereal", "RABI",
             "MED", "LOW", "LOW", 4, 6, "MED", "LOW", "YES",
             "temperate,subtropical", "Staple cereal crop"),
            ("RICE", "Rice (Paddy)", "Cereal", "KHARIF",
             "HIGH", "HIGH", "MED", 4, 6, "MED", "LOW", "YES",
             "tropical,subtropical", "Water-intensive staple"),
            ("MILLET", "Pearl Millet (Bajra)", "Millet", "KHARIF",
             "LOW", "LOW", "LOW", 3, 4, "LOW", "LOW", "YES",
             "arid,semi-arid", "Drought-tolerant grain"),
            ("MANGO", "Mango", "Fruit", "PERENNIAL",
             "MED", "MED", "LOW", 36, 60, "HIGH", "HIGH", "NO",
             "tropical,subtropical", "Long gestation orchard crop"),
            ("CAPSICUM", "Capsicum / Bell Pepper", "Vegetable", "RABI,KHARIF",
             "HIGH", "HIGH", "MED", 2, 4, "VERY_HIGH", "HIGH", "NO",
             "tropical,subtropical", "High-value protected cultivation crop"),
            ("GROUNDNUT", "Groundnut", "Oilseed", "KHARIF",
             "LOW", "MED", "MED", 4, 5, "MED", "LOW", "YES",
             "semi-arid,tropical", "Good for rainfed areas"),
            ("ONION", "Onion", "Vegetable", "RABI,KHARIF",
             "MED", "MED", "HIGH", 4, 6, "HIGH", "MED", "YES",
             "subtropical,temperate", "High price volatility"),
        ],
    )

    conn.executemany(
        """INSERT INTO crop_practice_compatibility (
            crop_id, practice_code, compatibility, compatibility_score,
            role_hint, rationale
        ) VALUES (?,?,?,?,?,?)""",
        [
            ("TOMATO", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Standard open field vegetable"),
            ("TOMATO", "POLYHOUSE", "GOOD", 1.0, "PRIMARY", "Ideal polyhouse crop"),
            ("WHEAT", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Standard cereal crop"),
            ("WHEAT", "RAIN_FED", "MED", 0.6, "PRIMARY", "Possible in good rainfall zones"),
            ("RICE", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Standard paddy cultivation"),
            ("MILLET", "RAIN_FED", "GOOD", 1.0, "PRIMARY", "Ideal dryland crop"),
            ("MILLET", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Works in open field too"),
            ("MANGO", "ORCHARD", "GOOD", 1.0, "PRIMARY", "Classic orchard crop"),
            ("CAPSICUM", "POLYHOUSE", "GOOD", 1.0, "PRIMARY", "Best in protected cultivation"),
            ("CAPSICUM", "OPEN_FIELD", "MED", 0.6, "PRIMARY", "Possible but lower yield"),
            ("GROUNDNUT", "RAIN_FED", "GOOD", 1.0, "PRIMARY", "Ideal rainfed oilseed"),
            ("GROUNDNUT", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Standard open field crop"),
            ("ONION", "OPEN_FIELD", "GOOD", 1.0, "PRIMARY", "Standard open field vegetable"),
            ("TOMATO", "INTEGRATED", "GOOD", 1.0, "PRIMARY", "Good component for IFS"),
            ("GROUNDNUT", "INTEGRATED", "MED", 0.6, "INTERCROP", "Can be intercropped in IFS"),
            ("WHEAT", "INTEGRATED", "MED", 0.6, "INTERCROP", "Seasonal component in IFS"),
        ],
    )
    conn.commit()
