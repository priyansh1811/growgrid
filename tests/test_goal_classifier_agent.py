"""Tests for Agent 2 — Goal Classifier."""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from growgrid_core.agents.step_2_goal_classifier_agent import (
    _BASE_TEMPLATES,
    SCORING_DIMENSIONS,
    GoalClassifierAgent,
)
from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import PlanRequest, WeightVector


def _run_goal_agent(request: PlanRequest) -> dict:
    """Helper: runs validation then goal classifier."""
    state = ValidationAgent().run({}, request)
    return GoalClassifierAgent().run(state, request)


class TestBaseTemplates:
    def test_all_goals_have_templates(self):
        for goal in Goal:
            assert goal in _BASE_TEMPLATES

    def test_templates_sum_to_one(self):
        for goal, template in _BASE_TEMPLATES.items():
            total = sum(template.values())
            assert math.isclose(total, 1.0, abs_tol=0.01), f"{goal}: {total}"


class TestWeightOutput:
    def test_weights_sum_to_one(self, sample_request: PlanRequest):
        state = _run_goal_agent(sample_request)
        w: WeightVector = state["goal_weights"]
        total = w.profit + w.risk + w.water + w.labour + w.time + w.capex
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_all_weights_positive(self, sample_request: PlanRequest):
        state = _run_goal_agent(sample_request)
        w: WeightVector = state["goal_weights"]
        for v in w.as_dict().values():
            assert v > 0

    def test_explanation_present(self, sample_request: PlanRequest):
        state = _run_goal_agent(sample_request)
        assert "goal_explanation" in state
        assert len(state["goal_explanation"]) > 20


class TestConstraintTightening:
    def test_low_water_boosts_water_weight(self):
        """When water=LOW, the water weight should be higher than the base template."""
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=500_000,  # high budget → low capex tightness
            labour_availability=LabourLevel.HIGH,  # no labour tightness
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=5.0,  # long horizon → low time tightness
            risk_tolerance=RiskLevel.HIGH,  # no risk tightness
        )
        state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        base_water = _BASE_TEMPLATES[Goal.MAXIMIZE_PROFIT]["water"]
        assert w.water > base_water

    def test_no_tightness_returns_base(self):
        """All resources HIGH/abundant → tightness all 0 → base template unchanged."""
        req = PlanRequest(
            location="Test",
            land_area_acres=10.0,
            water_availability=WaterLevel.HIGH,  # tightness 0
            irrigation_source=IrrigationSource.DRIP,
            budget_total_inr=2_000_000,  # 200k/acre → tightness 0.1
            labour_availability=LabourLevel.HIGH,  # tightness 0
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=10.0,  # 120 months → tightness 0.1
            risk_tolerance=RiskLevel.HIGH,  # tightness 0
        )
        state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        base = _BASE_TEMPLATES[Goal.MAXIMIZE_PROFIT]
        # profit tightness is always 0, so profit weight should be very close to base
        # (only shifted slightly by the small tightness in time and capex)
        assert math.isclose(w.profit, base["profit"], abs_tol=0.02)

    def test_short_horizon_boosts_time_weight(self):
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.HIGH,
            irrigation_source=IrrigationSource.DRIP,
            budget_total_inr=1_000_000,
            labour_availability=LabourLevel.HIGH,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=0.5,  # 6 months → tightness 1.0
            risk_tolerance=RiskLevel.HIGH,
        )
        state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        base_time = _BASE_TEMPLATES[Goal.STABLE_INCOME]["time"]
        assert w.time > base_time

    def test_low_budget_boosts_capex_weight(self):
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.HIGH,
            irrigation_source=IrrigationSource.CANAL,
            budget_total_inr=100_000,  # 20k/acre → tightness 1.0
            labour_availability=LabourLevel.HIGH,
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=5.0,
            risk_tolerance=RiskLevel.HIGH,
        )
        state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        base_capex = _BASE_TEMPLATES[Goal.MAXIMIZE_PROFIT]["capex"]
        assert w.capex > base_capex


class TestAllGoals:
    @pytest.mark.parametrize("goal", list(Goal))
    def test_each_goal_produces_valid_weights(self, goal: Goal):
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=300_000,
            labour_availability=LabourLevel.MED,
            goal=goal,
            time_horizon_years=2.0,
            risk_tolerance=RiskLevel.MED,
        )
        state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        total = sum(w.as_dict().values())
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_unknown_goal_uses_equal_weights_fallback(self):
        """When goal has no AHP template, agent uses equal weights and does not raise."""
        reduced_templates = {g: t for g, t in _BASE_TEMPLATES.items() if g != Goal.FAST_ROI}
        req = PlanRequest(
            location="Test",
            land_area_acres=5.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=300_000,
            labour_availability=LabourLevel.MED,
            goal=Goal.FAST_ROI,
            time_horizon_years=2.0,
            risk_tolerance=RiskLevel.MED,
        )
        with patch(
            "growgrid_core.agents.step_2_goal_classifier_agent._BASE_TEMPLATES",
            reduced_templates,
        ):
            state = _run_goal_agent(req)
        w: WeightVector = state["goal_weights"]
        total = sum(w.as_dict().values())
        assert math.isclose(total, 1.0, abs_tol=1e-9)
        assert all(getattr(w, d) > 0 for d in SCORING_DIMENSIONS)
        assert "equal weights" in state["goal_explanation"].lower() or "no template" in state["goal_explanation"].lower()
