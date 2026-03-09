"""Agent 9 — Critic / Consistency Agent (Phase-1 stub).

Purpose: Red-team the complete plan and catch contradictions:
    - water LOW but high-water crop selected
    - budget mismatch
    - horizon mismatch
    - missing steps for perishable crops
Suggest minimal fixes.
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Red-team the plan for consistency issues. (Phase-1 stub)"""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("CriticAgent is a Phase-1 stub — returning placeholder.")

        state["critic_report"] = {
            "status": "stub",
            "issues": [],
            "fixes": [],
            "final_confidence": None,
            "message": "Critic agent not yet implemented. "
            "Will use LLM + deterministic rules for plan red-teaming.",
        }
        return state
