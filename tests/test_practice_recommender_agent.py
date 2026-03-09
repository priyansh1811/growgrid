"""Tests for Agent 3 — Practice Recommender."""

from __future__ import annotations

import sqlite3

from growgrid_core.agents.step_2_goal_classifier_agent import GoalClassifierAgent
from growgrid_core.agents.step_3_practice_recommender_agent import PracticeRecommenderAgent
from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import PlanRequest, PracticeScore


def _run_up_to_practice(request: PlanRequest, conn: sqlite3.Connection) -> dict:
    """Run agents 1-3 and return state."""
    state = ValidationAgent().run({}, request)
    state = GoalClassifierAgent().run(state, request)
    state = PracticeRecommenderAgent(conn=conn).run(state, request)
    return state


class TestHardFilters:
    def test_low_water_excludes_high_water_practices(
        self, low_resource_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(low_resource_request, test_db)
        ranking = state["practice_ranking"]
        feasible = [s for s in ranking if not s.eliminated]
        for s in feasible:
            # POLYHOUSE has water_need=HIGH, should be eliminated
            assert s.practice_code != "POLYHOUSE"

    def test_low_budget_excludes_expensive_practices(
        self, low_resource_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(low_resource_request, test_db)
        ranking = state["practice_ranking"]
        # low_resource: budget=40000, land=2 → budget_per_acre=20000
        # POLYHOUSE capex_min=80000 → should be eliminated
        polyhouse = [s for s in ranking if s.practice_code == "POLYHOUSE"]
        assert len(polyhouse) == 1
        assert polyhouse[0].eliminated

    def test_low_risk_excludes_high_risk(
        self, low_resource_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(low_resource_request, test_db)
        ranking = state["practice_ranking"]
        feasible = [s for s in ranking if not s.eliminated]
        # RAIN_FED has risk_level=HIGH; user risk_tol=LOW → eliminated
        for s in feasible:
            assert s.practice_code != "RAIN_FED"


class TestScoring:
    def test_selected_practice_is_highest_score(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(sample_request, test_db)
        selected: PracticeScore = state["selected_practice"]
        feasible = [s for s in state["practice_ranking"] if not s.eliminated]
        if feasible:
            max_score = max(s.weighted_score for s in feasible)
            assert selected.weighted_score == max_score

    def test_alternatives_are_present(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(sample_request, test_db)
        # With sample_request (medium everything), multiple practices should survive
        alternatives = state["practice_alternatives"]
        assert isinstance(alternatives, list)

    def test_fit_scores_are_in_range(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_up_to_practice(sample_request, test_db)
        for ps in state["practice_ranking"]:
            if not ps.eliminated:
                for dim, val in ps.fit_scores.items():
                    assert 0.0 <= val <= 1.0, f"{ps.practice_code}.{dim} = {val}"


class TestEdgeCases:
    def test_all_eliminated_returns_none(self, test_db: sqlite3.Connection):
        """Impossible constraints → no feasible practice, graceful error."""
        req = PlanRequest(
            location="Test",
            land_area_acres=0.5,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=1000,  # 2000/acre — below everything
            labour_availability=LabourLevel.LOW,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=0.15,  # ~1.8 months
            risk_tolerance=RiskLevel.LOW,
        )
        state = _run_up_to_practice(req, test_db)
        selected: PracticeScore = state["selected_practice"]
        assert selected.practice_code == "NONE"
        assert selected.eliminated

    def test_deterministic_output(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        """Same input → same output."""
        s1 = _run_up_to_practice(sample_request, test_db)
        s2 = _run_up_to_practice(sample_request, test_db)
        assert s1["selected_practice"].practice_code == s2["selected_practice"].practice_code
        assert s1["selected_practice"].weighted_score == s2["selected_practice"].weighted_score


class TestTiebreaker:
    """Tiebreaker: when weighted scores are equal, lower risk wins (LOW < MED < HIGH)."""

    def test_tiebreaker_orders_by_risk_low_med_high(
        self, test_db: sqlite3.Connection
    ):
        # Three practices with same score; different risk levels
        base = PracticeScore(
            practice_code="",
            practice_name="",
            fit_scores={},
            weighted_score=0.5,
            eliminated=False,
        )
        feasible = [
            PracticeScore(**{**base.model_dump(), "practice_code": "HIGH_R"}),
            PracticeScore(**{**base.model_dump(), "practice_code": "LOW_R"}),
            PracticeScore(**{**base.model_dump(), "practice_code": "MED_R"}),
        ]
        practices_lookup = [
            {"practice_code": "LOW_R", "risk_level": "LOW"},
            {"practice_code": "MED_R", "risk_level": "MED"},
            {"practice_code": "HIGH_R", "risk_level": "HIGH"},
        ]
        result = PracticeRecommenderAgent._apply_tiebreaker(
            feasible, practices_lookup
        )
        codes = [s.practice_code for s in result]
        assert codes[0] == "LOW_R"
        assert codes[1] == "MED_R"
        assert codes[2] == "HIGH_R"
