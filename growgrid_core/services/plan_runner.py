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
from growgrid_core.utils.types import PlanRequest, PlanResponse

logger = logging.getLogger(__name__)


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
    )
