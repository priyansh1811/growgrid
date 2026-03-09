"""Tests for Agent 5 — Agronomist Verifier (with mocked LLM + Tavily)."""

from __future__ import annotations

import sqlite3

from growgrid_core.agents.step_5_agronomist_verifier_agent import AgronomistVerifierAgent
from growgrid_core.agents.step_4_crop_recommender_agent import CropRecommenderAgent
from growgrid_core.agents.step_2_goal_classifier_agent import GoalClassifierAgent
from growgrid_core.agents.step_3_practice_recommender_agent import PracticeRecommenderAgent
from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.tools.llm_client import MockLLMClient
from growgrid_core.tools.tavily_client import MockTavilyClient
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.utils.types import (
    AgronomistVerification,
    CropPortfolioEntry,
    GrowGuide,
    PlanRequest,
)


def _run_full_pipeline(
    request: PlanRequest,
    conn: sqlite3.Connection,
    llm_responses: list[dict] | None = None,
    tavily_results: list[dict] | None = None,
) -> dict:
    """Run agents 1–5 with mocked externals, return state."""
    state = ValidationAgent().run({}, request)
    state = GoalClassifierAgent().run(state, request)
    state = PracticeRecommenderAgent(conn=conn).run(state, request)
    state = CropRecommenderAgent(conn=conn).run(state, request)

    mock_llm = MockLLMClient(responses=llm_responses or _default_llm_responses())
    mock_tavily = MockTavilyClient(results=tavily_results)

    agent = AgronomistVerifierAgent(
        llm_client=mock_llm,
        tavily_client=mock_tavily,
    )
    state = agent.run(state, request)
    return state


def _default_llm_responses() -> list[dict]:
    """Enough canned responses for evidence extraction + conflict + grow guide calls."""
    evidence_response = {
        "sowing_window": "June-July (Kharif) or October-November (Rabi)",
        "climate_suitability": "Suitable for tropical and subtropical climates",
        "irrigation_notes": "Moderate irrigation, drip preferred",
        "major_pests": "Fruit borer, leaf curl virus",
        "time_to_harvest": "3-5 months from transplanting",
        "hard_warnings": "",
    }
    conflict_response = {
        "claims": [
            {
                "claim": "Practice is feasible",
                "conflict_level": "NO_ISSUE",
                "explanation": "All constraints are met",
                "required_action": "",
            },
            {
                "claim": "Crop is suitable in location",
                "conflict_level": "MINOR_VARIATION",
                "explanation": "Slightly different sowing window",
                "required_action": "",
            },
        ],
        "overall_confidence": 0.85,
    }
    grow_guide_response = {
        "sowing_window": "June-July for Kharif season",
        "monthly_timeline": [
            "Month 1: Land preparation and sowing",
            "Month 2-3: Vegetative growth, first weeding",
            "Month 3-4: Flowering and fruiting",
            "Month 4-5: Harvest",
        ],
        "land_prep": "Deep ploughing, raised beds, FYM application",
        "irrigation_rules": "Drip irrigation every 3-4 days, reduce during rains",
        "fertilizer_plan": "Basal NPK 50:30:30, top dress N at 30 days",
        "pest_prevention": [
            "Use neem-based pesticides for fruit borer",
            "Remove and destroy infected plants",
            "Install yellow sticky traps",
        ],
        "harvest_notes": "Harvest at colour break stage for distant markets",
        "why_recommended": "Good fit for medium water and budget in Maharashtra",
        "when_not_recommended": "Not suitable in frost-prone areas without protection",
    }
    # Return enough responses for: N crops * (evidence + conflict + guide)
    # Providing extras so we don't run out
    return [evidence_response, conflict_response, grow_guide_response] * 5


class TestAgronomistBasic:
    def test_produces_verification(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_full_pipeline(sample_request, test_db)
        verification: AgronomistVerification = state["agronomist_verification"]
        assert isinstance(verification, AgronomistVerification)
        assert 0.0 <= verification.confidence_score <= 1.0

    def test_produces_grow_guides(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_full_pipeline(sample_request, test_db)
        guides: list[GrowGuide] = state["grow_guides"]
        assert isinstance(guides, list)
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        if portfolio:
            assert len(guides) == len(portfolio)
            for g in guides:
                assert g.sowing_window
                assert len(g.pest_prevention) > 0

    def test_grow_guide_schema_complete(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        state = _run_full_pipeline(sample_request, test_db)
        guides: list[GrowGuide] = state["grow_guides"]
        if guides:
            g = guides[0]
            assert g.crop_id
            assert g.crop_name
            assert g.land_prep
            assert g.irrigation_rules
            assert g.fertilizer_plan
            assert g.harvest_notes
            assert g.why_recommended
            assert g.when_not_recommended


class TestCacheIntegration:
    def test_cache_hit_skips_tavily(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection, tmp_path
    ):
        """When cache is primed, Tavily should NOT be called."""
        cache = ToolCache(db_path=tmp_path / "test_cache.db")
        mock_tavily = MockTavilyClient()
        mock_llm = MockLLMClient(responses=_default_llm_responses())

        # Run pipeline first to discover which crops are selected
        state = ValidationAgent().run({}, sample_request)
        state = GoalClassifierAgent().run(state, sample_request)
        state = PracticeRecommenderAgent(conn=test_db).run(state, sample_request)
        state = CropRecommenderAgent(conn=test_db).run(state, sample_request)

        # Pre-populate cache for each crop
        for entry in state["selected_crop_portfolio"]:
            cache_key = f"{sample_request.location}|{state['selected_practice'].practice_code}|{entry.crop_id}|v1"
            cache.set(cache_key, [{"title": "Cached", "url": "https://cached.com", "content": "Cached content"}])

        # Now run agronomist with cache
        agent = AgronomistVerifierAgent(
            llm_client=mock_llm,
            tavily_client=mock_tavily,
            cache=cache,
        )
        state = agent.run(state, sample_request)

        # Tavily should NOT have been called (all cache hits)
        assert len(mock_tavily.call_log) == 0
        cache.close()


class TestGracefulDegradation:
    def test_no_crops_produces_empty_output(
        self, test_db: sqlite3.Connection
    ):
        """When no practice/crops are feasible, agronomist returns safe defaults."""
        from growgrid_core.utils.enums import (
            Goal,
            IrrigationSource,
            LabourLevel,
            RiskLevel,
            WaterLevel,
        )

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
        state = _run_full_pipeline(req, test_db)
        verification: AgronomistVerification = state["agronomist_verification"]
        assert verification.confidence_score == 0.0
        assert state["grow_guides"] == []


class TestConflictHandling:
    def test_major_conflict_adds_warning(
        self, sample_request: PlanRequest, test_db: sqlite3.Connection
    ):
        """When LLM reports MAJOR_CONFLICT, warnings should be populated."""
        conflict_response = {
            "claims": [
                {
                    "claim": "Crop is suitable",
                    "conflict_level": "MAJOR_CONFLICT",
                    "explanation": "Crop not suited for this climate zone",
                    "required_action": "Replace with alternative",
                }
            ],
            "overall_confidence": 0.3,
        }
        evidence_response = {
            "sowing_window": "Not applicable",
            "climate_suitability": "Not suitable",
            "irrigation_notes": "N/A",
            "major_pests": "N/A",
            "time_to_harvest": "N/A",
            "hard_warnings": "Crop fails in this region",
        }
        grow_guide = _default_llm_responses()[2]

        responses = [evidence_response, conflict_response, grow_guide] * 5
        state = _run_full_pipeline(sample_request, test_db, llm_responses=responses)
        verification: AgronomistVerification = state["agronomist_verification"]
        assert any("major conflict" in w.lower() for w in verification.warnings)
