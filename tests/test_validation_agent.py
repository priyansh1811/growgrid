"""Tests for Agent 1 — Validation & Sanity Checker."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import PlanRequest, ValidatedProfile


@pytest.fixture
def agent() -> ValidationAgent:
    return ValidationAgent()


class TestDerivedFields:
    def test_budget_per_acre(self, agent: ValidationAgent, sample_request: PlanRequest):
        state = agent.run({}, sample_request)
        profile: ValidatedProfile = state["validated_profile"]
        assert profile.budget_per_acre == 300_000 / 5.0  # 60000

    def test_horizon_months(self, agent: ValidationAgent, sample_request: PlanRequest):
        state = agent.run({}, sample_request)
        profile: ValidatedProfile = state["validated_profile"]
        assert profile.horizon_months == 24  # 2.0 years * 12


class TestHardConstraints:
    def test_low_water_excludes_high(self, agent: ValidationAgent, low_resource_request: PlanRequest):
        state = agent.run({}, low_resource_request)
        dims = [c.dimension for c in state["hard_constraints"]]
        assert "water" in dims

    def test_low_labour_excludes_high(self, agent: ValidationAgent, low_resource_request: PlanRequest):
        state = agent.run({}, low_resource_request)
        dims = [c.dimension for c in state["hard_constraints"]]
        assert "labour" in dims

    def test_low_budget_excludes_polyhouse(self, agent: ValidationAgent, low_resource_request: PlanRequest):
        state = agent.run({}, low_resource_request)
        practice_exclusions = [
            c for c in state["hard_constraints"]
            if c.dimension == "practice" and c.operator == "exclude_practice_codes"
            and "POLYHOUSE" in c.threshold
        ]
        assert len(practice_exclusions) >= 1
        assert "budget" in practice_exclusions[0].reason.lower() or "protected" in practice_exclusions[0].reason.lower() or "labour" in practice_exclusions[0].reason.lower()

    def test_low_risk_excludes_high(self, agent: ValidationAgent, low_resource_request: PlanRequest):
        state = agent.run({}, low_resource_request)
        dims = [c.dimension for c in state["hard_constraints"]]
        assert "risk" in dims

    def test_high_budget_no_polyhouse_constraint(self, agent: ValidationAgent, high_budget_request: PlanRequest):
        state = agent.run({}, high_budget_request)
        budget_exclusions = [
            c for c in state["hard_constraints"]
            if c.dimension == "practice" and c.operator == "exclude_practice_codes"
            and "POLYHOUSE" in c.threshold
            and "budget" in c.reason.lower()
        ]
        assert len(budget_exclusions) == 0

    def test_med_water_no_water_constraint(self, agent: ValidationAgent, sample_request: PlanRequest):
        state = agent.run({}, sample_request)
        water_constraints = [c for c in state["hard_constraints"] if c.dimension == "water"]
        assert len(water_constraints) == 0


class TestSoftConstraints:
    def test_no_irrigation_prefers_rainfed(self, agent: ValidationAgent, low_resource_request: PlanRequest):
        state = agent.run({}, low_resource_request)
        prefs = [s.preference for s in state["soft_constraints"]]
        assert "prefer_rainfed" in prefs

    def test_med_water_penalises_high(self, agent: ValidationAgent, sample_request: PlanRequest):
        state = agent.run({}, sample_request)
        prefs = [s.preference for s in state["soft_constraints"]]
        assert "penalise_high_water" in prefs


class TestWarnings:
    def test_micro_plot_warning(self, agent: ValidationAgent):
        req = PlanRequest(
            location="Test",
            land_area_acres=0.1,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=10000,
            labour_availability=LabourLevel.MED,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=1.0,
            risk_tolerance=RiskLevel.MED,
        )
        state = agent.run({}, req)
        assert any("micro-plot" in w.lower() for w in state["warnings"])

    def test_low_budget_warning(self, agent: ValidationAgent):
        req = PlanRequest(
            location="Test",
            land_area_acres=3.0,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.NONE,
            budget_total_inr=30_000,  # 10000/acre — below 20000 threshold
            labour_availability=LabourLevel.LOW,
            goal=Goal.STABLE_INCOME,
            time_horizon_years=1.0,
            risk_tolerance=RiskLevel.LOW,
        )
        state = agent.run({}, req)
        assert any("tight budget" in w.lower() for w in state["warnings"])

    def test_short_horizon_warning(self, agent: ValidationAgent):
        req = PlanRequest(
            location="Test",
            land_area_acres=2.0,
            water_availability=WaterLevel.MED,
            irrigation_source=IrrigationSource.CANAL,
            budget_total_inr=100000,
            labour_availability=LabourLevel.MED,
            goal=Goal.FAST_ROI,
            time_horizon_years=0.3,  # ~3.6 months
            risk_tolerance=RiskLevel.MED,
        )
        state = agent.run({}, req)
        assert any("short" in w.lower() and "horizon" in w.lower() for w in state["warnings"])

    def test_very_large_budget_warning(self, agent: ValidationAgent):
        req = PlanRequest(
            location="Test",
            land_area_acres=10.0,
            water_availability=WaterLevel.HIGH,
            irrigation_source=IrrigationSource.DRIP,
            budget_total_inr=20_000_000,
            labour_availability=LabourLevel.HIGH,
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=5.0,
            risk_tolerance=RiskLevel.HIGH,
        )
        state = agent.run({}, req)
        assert any("verify" in w.lower() for w in state["warnings"])


class TestPlanRequestValidation:
    def test_invalid_enum_raises(self):
        with pytest.raises(ValidationError):
            PlanRequest(
                location="Test",
                land_area_acres=1.0,
                water_availability="SUPER_HIGH",  # invalid
                irrigation_source=IrrigationSource.NONE,
                budget_total_inr=10000,
                labour_availability=LabourLevel.MED,
                goal=Goal.STABLE_INCOME,
                time_horizon_years=1.0,
                risk_tolerance=RiskLevel.MED,
            )

    def test_zero_land_raises(self):
        with pytest.raises(ValidationError):
            PlanRequest(
                location="Test",
                land_area_acres=0,
                water_availability=WaterLevel.MED,
                irrigation_source=IrrigationSource.NONE,
                budget_total_inr=10000,
                labour_availability=LabourLevel.MED,
                goal=Goal.STABLE_INCOME,
                time_horizon_years=1.0,
                risk_tolerance=RiskLevel.MED,
            )

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            PlanRequest(
                location="Test",
                land_area_acres=1.0,
                # missing water_availability
                irrigation_source=IrrigationSource.NONE,
                budget_total_inr=10000,
                labour_availability=LabourLevel.MED,
                goal=Goal.STABLE_INCOME,
                time_horizon_years=1.0,
                risk_tolerance=RiskLevel.MED,
            )
