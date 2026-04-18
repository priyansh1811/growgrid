"""Pipeline orchestrator — runs all agents in sequence.

    from growgrid_core.services.plan_runner import run_pipeline
    response = run_pipeline(plan_request)
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.agents.step_1_validation_agent import ValidationAgent
from growgrid_core.agents.step_2_goal_classifier_agent import GoalClassifierAgent
from growgrid_core.agents.step_3_practice_recommender_agent import PracticeRecommenderAgent
from growgrid_core.agents.step_4_crop_recommender_agent import CropRecommenderAgent
from growgrid_core.agents.step_5_agronomist_verifier_agent import AgronomistVerifierAgent
from growgrid_core.agents.step_6_critic_agent import CriticAgent
from growgrid_core.agents.step_7_economist_agent import EconomistAgent
from growgrid_core.agents.step_9_field_layout_agent import FieldLayoutAgent
from growgrid_core.agents.step_10_govt_schemes_agent import GovtSchemesAgent
from growgrid_core.agents.step_11_report_composer_agent import ReportComposerAgent
from growgrid_core.config import DATAGOV_API_KEY, OPENAI_API_KEY, TAVILY_API_KEY
from growgrid_core.db.db_loader import load_all
from growgrid_core.tools.datagov_client import BaseDataGovMandiClient, DataGovMandiClient
from growgrid_core.tools.llm_client import BaseLLMClient, MockLLMClient, OpenAILLMClient
from growgrid_core.tools.tavily_client import BaseTavilyClient, MockTavilyClient, TavilyClient
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.db.queries import (
    get_icar_crop_calendar,
    get_icar_nutrient_plan,
    get_icar_pest_disease,
    get_icar_varieties,
    get_icar_weed_management,
)
from growgrid_core.utils.icar_matching import match_id_to_icar_names, normalize_state_for_icar
from growgrid_core.utils.location import parse_state_from_location
from growgrid_core.utils.season import detect_season
from growgrid_core.utils.types import (
    IcarAdvisory,
    IcarAdvisoryReport,
    IcarCalendarEntry,
    IcarNutrientPlan,
    IcarPestEntry,
    IcarVarietyEntry,
    IcarWeedEntry,
    PlanRequest,
    PlanResponse,
)

logger = logging.getLogger(__name__)


def _to_str(val: Any) -> str | None:
    """Safely coerce a DB value to str (handles float/int columns stored as text fields)."""
    if val is None:
        return None
    return str(val)


def _fallback_agronomist_mock_responses() -> list[dict]:
    """Canned responses for AgronomistVerifierAgent when API keys are missing (evidence, conflict, guide per crop)."""
    evidence = {
        "sowing_window": "Consult local extension",
        "climate_suitability": "Suitable for region",
        "irrigation_notes": "As per practice",
        "major_pests": "Apply IPM",
        "time_to_harvest": "As per crop",
        "hard_warnings": "",
    }
    conflict = {
        "claims": [{"claim": "Recommendation is feasible", "conflict_level": "NO_ISSUE", "explanation": "No conflict", "required_action": ""}],
        "overall_confidence": 0.85,
    }
    guide = {
        "sowing_window": "Consult local agricultural calendar",
        "monthly_timeline": ["Month 1: Land prep and sowing", "Month 2: Irrigation and weeding", "Month 3: Harvest"],
        "land_prep": "Standard preparation for the region",
        "irrigation_rules": "Follow local practice",
        "fertilizer_plan": "Balanced NPK as per soil test",
        "pest_prevention": ["Integrated pest management recommended"],
        "harvest_notes": "Harvest at maturity",
        "why_recommended": "Matches your constraints",
        "when_not_recommended": "When conditions differ significantly",
    }
    return [evidence, conflict, guide] * 10  # enough for many crops


def run_pipeline(
    request: PlanRequest,
    *,
    conn: sqlite3.Connection | None = None,
    llm_client: BaseLLMClient | None = None,
    tavily_client: BaseTavilyClient | None = None,
    cache: ToolCache | None = None,
    datagov_client: BaseDataGovMandiClient | None = None,
) -> PlanResponse:
    """Execute the full GrowGrid pipeline and return a PlanResponse.

    Args:
        request: Validated user inputs.
        conn: Optional pre-loaded DB connection (for testing).
        llm_client: Optional LLM client (for testing/mocking).
        tavily_client: Optional Tavily client (for testing/mocking).
        cache: Optional Tavily cache (for testing).
        datagov_client: Optional data.gov.in mandi price client (for testing/mocking).

    Returns:
        Fully populated PlanResponse.
    """
    db = conn or load_all()

    # Use real LLM client when API key is available, mock when missing
    _llm = llm_client
    if _llm is None:
        if (OPENAI_API_KEY or "").strip():
            _llm = OpenAILLMClient()
        else:
            _llm = MockLLMClient(responses=_fallback_agronomist_mock_responses())
    _tavily = tavily_client
    if _tavily is None:
        if (TAVILY_API_KEY or "").strip():
            _tavily = TavilyClient()
        else:
            _tavily = MockTavilyClient()

    _datagov = datagov_client
    if _datagov is None:
        if (DATAGOV_API_KEY or "").strip():
            _datagov = DataGovMandiClient()

    agents: list[BaseAgent] = [
        ValidationAgent(),
        GoalClassifierAgent(),
        PracticeRecommenderAgent(conn=db),
        CropRecommenderAgent(conn=db),
        AgronomistVerifierAgent(
            llm_client=_llm,
            tavily_client=_tavily,
            cache=cache,
        ),
        CriticAgent(),
        EconomistAgent(conn=db, llm_client=_llm, tavily_client=_tavily, cache=cache, datagov_client=_datagov),
        FieldLayoutAgent(conn=db),
        GovtSchemesAgent(conn=db),
        ReportComposerAgent(),
    ]

    state: dict[str, Any] = {}

    for agent in agents:
        agent_name = agent.__class__.__name__
        logger.info("Running %s...", agent_name)
        try:
            state = agent.run(state, request)
        except Exception:
            logger.exception("Agent %s failed", agent_name)
            raise

    # ── Build ICAR advisory report ─────────────────────────────────
    icar_advisory = _build_icar_advisory(db, state)

    return PlanResponse(
        validated_profile=state["validated_profile"],
        hard_constraints=state["hard_constraints"],
        soft_constraints=state["soft_constraints"],
        warnings=state["warnings"],
        conflicts=state.get("conflicts", []),
        goal_weights=state["goal_weights"],
        goal_explanation=state["goal_explanation"],
        practice_ranking=state["practice_ranking"],
        selected_practice=state["selected_practice"],
        practice_alternatives=state["practice_alternatives"],
        selected_practice_reason=state.get("selected_practice_reason", ""),
        crop_ranking=state["crop_ranking"],
        selected_crop_portfolio=state["selected_crop_portfolio"],
        selected_crop_portfolio_reason=state.get("selected_crop_portfolio_reason", ""),
        agronomist_verification=state["agronomist_verification"],
        grow_guides=state["grow_guides"],
        critic_report=state.get("critic_report"),
        report_payload=state.get("report_payload"),
        economics=state.get("economics"),
        economist_output=state.get("economist_output"),
        field_layout=state.get("field_layout"),
        schemes=state.get("schemes"),
        icar_advisory=icar_advisory,
    )


def _build_icar_advisory(
    conn: sqlite3.Connection,
    state: dict[str, Any],
) -> IcarAdvisoryReport | None:
    """Build ICAR advisory report for all crops in the portfolio.

    Queries all 5 ICAR tables for each crop and returns structured data
    for the frontend ICAR Advisory tab.
    """
    try:
        profile = state.get("validated_profile")
        portfolio = state.get("selected_crop_portfolio", [])
        if not profile or not portfolio:
            return None

        state_name = parse_state_from_location(profile.location)
        if not state_name:
            return None

        season = detect_season(profile.planning_month) if profile.planning_month else "rabi"
        icar_states = normalize_state_for_icar(state_name)
        if not icar_states:
            return None

        advisories: list[IcarAdvisory] = []

        for entry in portfolio:
            icar_names = match_id_to_icar_names(entry.crop_id)
            if not icar_names:
                icar_names = [entry.crop_name.lower()]

            advisory = IcarAdvisory(
                state=icar_states[0],
                season=season,
                crop_name=entry.crop_name,
                crop_id=entry.crop_id,
            )

            found = False
            for icar_state in icar_states:
                for name in icar_names:
                    # Calendar
                    cal_rows = get_icar_crop_calendar(conn, icar_state, season, name)
                    for r in cal_rows:
                        advisory.calendar.append(IcarCalendarEntry(
                            crop_name=_to_str(r.get("crop_name")) or "",
                            sub_region=_to_str(r.get("sub_region")),
                            sow_start_month=int(r["sow_start_month"]) if r.get("sow_start_month") else None,
                            sow_end_month=int(r["sow_end_month"]) if r.get("sow_end_month") else None,
                            harvest_month_range=_to_str(r.get("harvest_month_range")),
                            seed_rate_kg_ha=r.get("seed_rate_kg_ha"),
                            row_spacing_cm=r.get("row_spacing_cm"),
                            plant_spacing_cm=r.get("plant_spacing_cm"),
                            duration_days=int(r["duration_days"]) if r.get("duration_days") else None,
                            notes=_to_str(r.get("notes")),
                        ))
                        found = True

                    # Nutrient plan
                    nut_rows = get_icar_nutrient_plan(conn, icar_state, season, name)
                    for r in nut_rows:
                        advisory.nutrient_plans.append(IcarNutrientPlan(
                            crop_name=_to_str(r.get("crop_name")) or "",
                            sub_region=_to_str(r.get("sub_region")),
                            N_kg_ha=r.get("N_kg_ha"),
                            P_kg_ha=r.get("P_kg_ha"),
                            K_kg_ha=r.get("K_kg_ha"),
                            FYM_t_ha=r.get("FYM_t_ha"),
                            zinc_sulphate_kg_ha=r.get("zinc_sulphate_kg_ha"),
                            other_micronutrients=_to_str(r.get("other_micronutrients")),
                            biofertilizers=_to_str(r.get("biofertilizers")),
                            split_schedule=_to_str(r.get("split_schedule")),
                            application_notes=_to_str(r.get("application_notes")),
                        ))
                        found = True

                    # Pest/disease
                    pest_rows = get_icar_pest_disease(conn, icar_state, season, name)
                    for r in pest_rows:
                        advisory.pests.append(IcarPestEntry(
                            crop_name=_to_str(r.get("crop_name")) or "",
                            sub_region=_to_str(r.get("sub_region")),
                            pest_or_disease_name=_to_str(r.get("pest_or_disease_name")) or "",
                            type=_to_str(r.get("type")),
                            monitor_start_month=int(r["monitor_start_month"]) if r.get("monitor_start_month") else None,
                            monitor_end_month=int(r["monitor_end_month"]) if r.get("monitor_end_month") else None,
                            chemical_control=_to_str(r.get("chemical_control")),
                            bio_control=_to_str(r.get("bio_control")),
                            threshold_note=_to_str(r.get("threshold_note")),
                        ))
                        found = True

                    # Varieties
                    var_rows = get_icar_varieties(conn, icar_state, season, name)
                    for r in var_rows:
                        advisory.varieties.append(IcarVarietyEntry(
                            crop_name=_to_str(r.get("crop_name")) or "",
                            sub_region=_to_str(r.get("sub_region")),
                            variety_names=_to_str(r.get("variety_names")),
                            variety_type=_to_str(r.get("variety_type")),
                            duration_type=_to_str(r.get("duration_type")),
                            purpose=_to_str(r.get("purpose")),
                        ))
                        found = True

                    # Weed management
                    weed_rows = get_icar_weed_management(conn, icar_state, season, name)
                    for r in weed_rows:
                        advisory.weed_management.append(IcarWeedEntry(
                            crop_name=r.get("crop_name", ""),
                            sub_region=r.get("sub_region"),
                            pre_emergence_herbicide=_to_str(r.get("pre_emergence_herbicide")),
                            pre_em_dose=_to_str(r.get("pre_em_dose")),
                            pre_em_timing_das=_to_str(r.get("pre_em_timing_das")),
                            post_emergence_herbicide=_to_str(r.get("post_emergence_herbicide")),
                            post_em_dose=_to_str(r.get("post_em_dose")),
                            post_em_timing_das=_to_str(r.get("post_em_timing_das")),
                            manual_weeding_schedule=_to_str(r.get("manual_weeding_schedule")),
                        ))
                        found = True

                    if found:
                        break
                if found:
                    break

            if found:
                advisories.append(advisory)

        if not advisories:
            return None

        return IcarAdvisoryReport(
            state=icar_states[0],
            season=season,
            advisories=advisories,
        )

    except Exception as exc:
        logger.warning("Failed to build ICAR advisory report: %s", exc)
        return None
