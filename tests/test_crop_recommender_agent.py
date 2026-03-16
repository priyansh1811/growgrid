"""Tests for Agent 4 — Crop Recommender."""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.agents.step_2_goal_classifier_agent import GoalClassifierAgent
from growgrid_core.agents.step_3_practice_recommender_agent import PracticeRecommenderAgent
from growgrid_core.agents.step_4_crop_recommender_agent import CropRecommenderAgent
from growgrid_core.tools.llm_client import MockLLMClient
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import CropPortfolioEntry, PlanRequest


def _run_up_to_crop(request: PlanRequest, conn: sqlite3.Connection) -> dict:
    """Run agents 1-4 and return state."""
    state = ValidationAgent().run({}, request)
    state = GoalClassifierAgent().run(state, request)
    state = PracticeRecommenderAgent(conn=conn).run(state, request)
    state = CropRecommenderAgent(conn=conn).run(state, request)
    return state


class TestHardFilters:
    def test_low_water_excludes_high_water_crops(
        self, low_resource_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_crop(low_resource_request, test_db)
        ranking = state["crop_ranking"]
        feasible = [s for s in ranking if not s.eliminated]
        for s in feasible:
            # RICE has water_need=HIGH → should be eliminated
            assert s.crop_id != "RICE"

    def test_short_horizon_excludes_long_crops(
        self, test_db: sqlite3.Connection
    ):
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=300_000,
            labour_availability=LabourLevel.MED,
            goal=Goal.FAST_ROI,
            time_horizon_years=0.5,  # 6 months
            risk_tolerance=RiskLevel.MED,
        )
        state = _run_up_to_crop(req, test_db)
        ranking = state["crop_ranking"]
        feasible = [s for s in ranking if not s.eliminated]
        for s in feasible:
            # No crop with time_min > 6 should survive
            assert s.crop_id != "MANGO"


class TestScoring:
    def test_crop_scores_in_range(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_crop(sample_request, test_db)
        for cs in state["crop_ranking"]:
            if not cs.eliminated:
                assert 0.0 <= cs.final_score <= 1.0, f"{cs.crop_id}: {cs.final_score}"

    def test_compatibility_multiplier_applied(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_crop(sample_request, test_db)
        for cs in state["crop_ranking"]:
            if not cs.eliminated and cs.compatibility_score < 1.0:
                # final = weighted_sum * compat, so final < weighted_sum
                ws = sum(
                    cs.fit_scores.get(d, 0)
                    for d in ["profit", "risk", "water", "labour", "time"]
                )
                # Just check final_score <= weighted_sum (approximately)
                assert cs.final_score <= ws + 0.01


class TestPortfolio:
    def test_single_crop_for_small_land_high_risk(
        self, test_db: sqlite3.Connection
    ):
        req = PlanRequest(
            location="Test",
            land_area_acres=1.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=50_000,
            labour_availability=LabourLevel.MED,
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=1.0,
            risk_tolerance=RiskLevel.HIGH,
        )
        state = _run_up_to_crop(req, test_db)
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        assert len(portfolio) == 1
        assert portfolio[0].area_fraction == 1.0

    def test_multiple_crops_for_large_land_low_risk(
        self, test_db: sqlite3.Connection
    ):
        """Large land + low risk → diversification → 2+ crops.
        Use OPEN_FIELD which has many compatible crops in test data."""
        req = PlanRequest(
            location="Test",
            land_area_acres=6.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=200_000,  # 33k/acre — keeps OPEN_FIELD feasible
            labour_availability=LabourLevel.MED,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=2.0,
            risk_tolerance=RiskLevel.LOW,
        )
        state = _run_up_to_crop(req, test_db)
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        assert len(portfolio) >= 2

    def test_area_fractions_sum_to_one(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_crop(sample_request, test_db)
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        if portfolio:
            total = sum(e.area_fraction for e in portfolio)
            assert abs(total - 1.0) < 1e-9


class TestEdgeCases:
    def test_no_practice_means_no_crops(self, test_db: sqlite3.Connection):
        """When no practice was feasible, crop agent returns empty."""
        req = PlanRequest(
            location="Test",
            land_area_acres=0.5,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=1000,
            labour_availability=LabourLevel.LOW,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=0.15,
            risk_tolerance=RiskLevel.LOW,
        )
        state = _run_up_to_crop(req, test_db)
        assert state["selected_crop_portfolio"] == []

    def test_deterministic(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        s1 = _run_up_to_crop(sample_request, test_db)
        s2 = _run_up_to_crop(sample_request, test_db)
        p1 = [e.crop_id for e in s1["selected_crop_portfolio"]]
        p2 = [e.crop_id for e in s2["selected_crop_portfolio"]]
        assert p1 == p2

    def test_selected_crop_portfolio_reason_always_present(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        """With LLM layer disabled, deterministic reason is set."""
        state = _run_up_to_crop(sample_request, test_db)
        assert "selected_crop_portfolio_reason" in state
        assert isinstance(state["selected_crop_portfolio_reason"], str)
        assert len(state["selected_crop_portfolio_reason"]) > 0

    def test_llm_explanation_used_when_mock_provided(self, sample_request: PlanRequest, test_db: sqlite3.Connection):
        """When LLM layer is enabled and mock returns text, that text is used as reason."""
        # No user_context in sample_request → only complete_text() is called (portfolio explanation)
        mock = MockLLMClient(responses=[{"raw_text": "This portfolio fits your land and risk profile."}])
        with patch("growgrid_core.agents.step_4_crop_recommender_agent.CROP_LLM_LAYER_ENABLED", True):
            state = ValidationAgent().run({}, sample_request)
            state = GoalClassifierAgent().run(state, sample_request)
            state = PracticeRecommenderAgent(conn=test_db).run(state, sample_request)
            state = CropRecommenderAgent(conn=test_db, llm_client=mock).run(state, sample_request)
        assert "selected_crop_portfolio_reason" in state
        assert "This portfolio fits your land and risk profile" in state["selected_crop_portfolio_reason"]
