"""Agent 10 — Report Composer Agent (Phase-1 stub).

Purpose: Assemble all pipeline outputs into a structured report:
    - Executive summary
    - Practice + reasoning
    - Crops + area split + grow guides
    - Economics tables
    - Schemes section
    - Layout section
    - Risks & mitigations
Produce PDF-ready sections.
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class ReportComposerAgent(BaseAgent):
    """Compose structured report payload from plan state. (Phase-1 stub)"""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("ReportComposerAgent is a Phase-1 stub — returning placeholder.")

        state["report_payload"] = {
            "status": "stub",
            "sections": {
                "executive_summary": None,
                "practice_selection": None,
                "crop_portfolio": None,
                "grow_guides": None,
                "economics": None,
                "schemes": None,
                "field_layout": None,
                "risks_mitigations": None,
            },
            "pdf_ready": False,
            "message": "Report composer not yet implemented.",
        }
        return state
