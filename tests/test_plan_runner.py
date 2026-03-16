"""Integration test — full pipeline end-to-end with mocked externals."""

from __future__ import annotations

import sqlite3

from growgrid_core.services.plan_runner import run_pipeline
from growgrid_core.tools.llm_client import MockLLMClient
from growgrid_core.tools.tavily_client import MockTavilyClient
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import PlanRequest, PlanResponse


def _mock_llm_responses() -> list[dict]:
    evidence = {
        "sowing_window": "June-July",
        "climate_suitability": "Suitable",
        "irrigation_notes": "Moderate",
        "major_pests": "Aphids",
        "time_to_harvest": "4 months",
        "hard_warnings": "",
    }
    conflict = {
        "claims": [
            {
                "claim": "Practice is feasible",
                "conflict_level": "NO_ISSUE",
                "explanation": "All good",
                "required_action": "",
            }
        ],
        "overall_confidence": 0.9,
    }
    guide = {
        "sowing_window": "June-July",
        "monthly_timeline": ["Month 1: Sow", "Month 2: Grow", "Month 3: Harvest"],
        "land_prep": "Plough and level",
        "irrigation_rules": "Every 3 days",
        "fertilizer_plan": "NPK 50:30:30",
        "pest_prevention": ["Neem spray", "Crop rotation", "Trap crops"],
        "harvest_notes": "Harvest at maturity",
        "why_recommended": "Good fit",
        "when_not_recommended": "Frost areas",
    }
    return [evidence, conflict, guide] * 10


class TestFullPipeline:
    def test_mid_range_farmer(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        response = run_pipeline(
            sample_request,
            conn=test_db,
            llm_client=MockLLMClient(responses=_mock_llm_responses()),
            tavily_client=MockTavilyClient(),
        )
        assert isinstance(response, PlanResponse)
        assert response.validated_profile.budget_per_acre == 60_000.0
        assert response.validated_profile.horizon_months == 24
        assert not response.selected_practice.eliminated
        assert len(response.selected_crop_portfolio) >= 1
        assert response.agronomist_verification.confidence_score > 0

    def test_low_resource_farmer(
        self, low_resource_request: PlanRequest, test_db: sqlite3.Connection
    ):
        response = run_pipeline(
            low_resource_request,
            conn=test_db,
            llm_client=MockLLMClient(responses=_mock_llm_responses()),
            tavily_client=MockTavilyClient(),
        )
        assert isinstance(response, PlanResponse)
        # Should have constraints about water and labour
        dims = [c.dimension for c in response.hard_constraints]
        assert "water" in dims
        assert "labour" in dims

    def test_high_budget_farmer(
        self, high_budget_request: PlanRequest, test_db: sqlite3.Connection
    ):
        response = run_pipeline(
            high_budget_request,
            conn=test_db,
            llm_client=MockLLMClient(responses=_mock_llm_responses()),
            tavily_client=MockTavilyClient(),
        )
        assert isinstance(response, PlanResponse)
        assert response.validated_profile.budget_per_acre == 200_000.0
        assert not response.selected_practice.eliminated

    def test_response_serializable(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        """PlanResponse should be JSON-serializable."""
        response = run_pipeline(
            sample_request,
            conn=test_db,
            llm_client=MockLLMClient(responses=_mock_llm_responses()),
            tavily_client=MockTavilyClient(),
        )
        json_str = response.model_dump_json()
        assert len(json_str) > 100

    def test_impossible_constraints(self, test_db: sqlite3.Connection):
        """Impossible request → pipeline completes with NONE practice."""
        req = PlanRequest(
            location="Test",
            land_area_acres=0.5,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=500,
            labour_availability=LabourLevel.LOW,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=0.1,
            risk_tolerance=RiskLevel.LOW,
        )
        response = run_pipeline(
            req,
            conn=test_db,
            llm_client=MockLLMClient(responses=_mock_llm_responses()),
            tavily_client=MockTavilyClient(),
        )
        assert response.selected_practice.eliminated
        assert response.selected_crop_portfolio == []
