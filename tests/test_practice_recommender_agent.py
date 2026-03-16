"""Tests for Agent 3 — Practice Recommender."""

from __future__ import annotations

import sqlite3

from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.agents.step_2_goal_classifier_agent import GoalClassifierAgent
from growgrid_core.agents.step_3_practice_recommender_agent import PracticeRecommenderAgent
from growgrid_core.utils.location import parse_state_from_location
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


class TestExpertSignals:
    def test_parse_state_from_location_prefers_state_first(self):
        assert parse_state_from_location("Maharashtra, Pune") == "Maharashtra"
        assert parse_state_from_location("Kerala") == "Kerala"

    def test_practice_with_no_user_feasible_crop_pathway_is_eliminated(
        self, test_db: sqlite3.Connection
    ):
        test_db.execute(
            """INSERT INTO practice_master (
                practice_code, practice_name, water_need, labour_need, risk_level,
                time_to_first_income_months_min, time_to_first_income_months_max,
                capex_min_per_acre_inr, capex_max_per_acre_inr,
                opex_min_per_acre_inr, opex_max_per_acre_inr,
                profit_potential, perishability_exposure, storage_dependency,
                suitable_when, not_suitable_when, source_id, source_tier
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "SPECIAL", "Specialist Practice", "MED", "MED", "MED",
                2, 4, 5000, 12000, 4000, 8000,
                "HIGH", "MED", "LOW",
                "Niche model", "Not for everyone", "SRC999", "T2",
            ),
        )
        test_db.execute(
            """INSERT INTO crop_master (
                crop_id, crop_name, category, seasons_supported,
                water_need, labour_need, risk_level,
                time_to_first_income_months_min, time_to_first_income_months_max,
                profit_potential, perishability, storage_need,
                climate_tags, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "RISKY_SPECIAL", "Risky Special Crop", "Vegetable", "KHARIF",
                "HIGH", "HIGH", "HIGH", 2, 3, "HIGH", "HIGH", "NO",
                "humid", "Only fits very aggressive growers",
            ),
        )
        test_db.execute(
            """INSERT INTO crop_practice_compatibility (
                crop_id, practice_code, compatibility, compatibility_score, role_hint, rationale
            ) VALUES (?,?,?,?,?,?)""",
            ("RISKY_SPECIAL", "SPECIAL", "GOOD", 1.0, "PRIMARY", "Only crop for this practice"),
        )
        test_db.commit()

        req = PlanRequest(
            location="Maharashtra, Pune",
            land_area_acres=1.0,
            water_availability=WaterLevel.LOW,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=50_000,
            labour_availability=LabourLevel.MED,
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=1.0,
            risk_tolerance=RiskLevel.LOW,
        )
        state = _run_up_to_practice(req, test_db)
        special = next(s for s in state["practice_ranking"] if s.practice_code == "SPECIAL")
        assert special.eliminated is True
        assert "No crops under this practice" in (special.elimination_reason or "")

    def test_irrigation_suitability_changes_practice_score(
        self, test_db: sqlite3.Connection
    ):
        test_db.executemany(
            """INSERT INTO practice_irrigation_suitability (
                practice_code, irrigation_source, suitability, rationale
            ) VALUES (?,?,?,?)""",
            [
                ("OPEN_FIELD", "BOREWELL", "MED", "usable"),
                ("OPEN_FIELD", "DRIP", "GOOD", "better"),
                ("POLYHOUSE", "BOREWELL", "MED", "usable"),
                ("POLYHOUSE", "DRIP", "GOOD", "best"),
                ("ORCHARD", "BOREWELL", "MED", "usable"),
                ("ORCHARD", "DRIP", "GOOD", "best"),
                ("RAIN_FED", "BOREWELL", "MED", "neutral"),
                ("INTEGRATED", "BOREWELL", "MED", "neutral"),
            ],
        )
        test_db.commit()

        borewell_req = PlanRequest(
            location="Maharashtra, Pune",
            land_area_acres=5.0,
            water_availability=WaterLevel.HIGH,
            irrigation_source=IrrigationSource.BOREWELL,
            budget_total_inr=1_500_000,
            labour_availability=LabourLevel.HIGH,
            goal=Goal.MAXIMIZE_PROFIT,
            time_horizon_years=3.0,
            risk_tolerance=RiskLevel.MED,
        )
        drip_req = borewell_req.model_copy(update={"irrigation_source": IrrigationSource.DRIP})

        borewell_state = _run_up_to_practice(borewell_req, test_db)
        drip_state = _run_up_to_practice(drip_req, test_db)

        borewell_polyhouse = next(
            s for s in borewell_state["practice_ranking"] if s.practice_code == "POLYHOUSE"
        )
        drip_polyhouse = next(
            s for s in drip_state["practice_ranking"] if s.practice_code == "POLYHOUSE"
        )
        assert drip_polyhouse.weighted_score > borewell_polyhouse.weighted_score
