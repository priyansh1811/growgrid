"""Agent 8 — Field Layout Planner Agent (Phase-1 stub).

Purpose: Convert crop portfolio + area split into a spatial layout:
    - spacing plan per crop
    - plant/tree count
    - block-level layout suggestions

Requires:
    - crop_spacing_open_field table
    - crop_spacing_orchard table
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class FieldLayoutAgent(BaseAgent):
    """Generate field layout plan from crop portfolio. (Phase-1 stub)"""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("FieldLayoutAgent is a Phase-1 stub — returning placeholder.")

        state["field_layout"] = {
            "status": "stub",
            "layout_plan": None,
            "plant_counts": {},
            "spacing_used": {},
            "message": "Field layout agent not yet implemented. "
            "Requires crop_spacing tables.",
        }
        return state
