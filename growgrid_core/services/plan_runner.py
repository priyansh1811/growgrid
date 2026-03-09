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
from growgrid_core.db.db_loader import load_all
from growgrid_core.tools.llm_client import BaseLLMClient
from growgrid_core.tools.tavily_client import BaseTavilyClient
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.utils.types import PlanRequest, PlanResponse

logger = logging.getLogger(__name__)


def run_pipeline(
    request: PlanRequest,
    *,
    conn: sqlite3.Connection | None = None,
    llm_client: BaseLLMClient | None = None,
    tavily_client: BaseTavilyClient | None = None,
    cache: ToolCache | None = None,
) -> PlanResponse:
    """Execute the full GrowGrid pipeline and return a PlanResponse.

    Args:
        request: Validated user inputs.
        conn: Optional pre-loaded DB connection (for testing).
        llm_client: Optional LLM client (for testing/mocking).
        tavily_client: Optional Tavily client (for testing/mocking).
        cache: Optional Tavily cache (for testing).

    Returns:
        Fully populated PlanResponse.
    """
    db = conn or load_all()

    agents: list[BaseAgent] = [
        ValidationAgent(),
        GoalClassifierAgent(),
        PracticeRecommenderAgent(conn=db),
        CropRecommenderAgent(conn=db),
        AgronomistVerifierAgent(
            llm_client=llm_client,
            tavily_client=tavily_client,
            cache=cache,
        ),
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
    )
