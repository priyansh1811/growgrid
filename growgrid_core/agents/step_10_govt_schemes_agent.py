"""Agent 7 — Government Schemes RAG Agent (Phase-1 stub).

Purpose: Retrieve relevant government schemes using vector search
over scheme documents, matched by user location, practice, and crop tags.

Requires:
    - schemes_metadata table
    - vector index (ChromaDB or similar) over scheme PDFs/documents
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class GovtSchemesAgent(BaseAgent):
    """Retrieve relevant government schemes via RAG. (Phase-1 stub)"""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("GovtSchemesAgent is a Phase-1 stub — returning placeholder.")

        state["schemes"] = {
            "status": "stub",
            "matched_schemes": [],
            "eligibility_checklist": [],
            "application_steps": [],
            "message": "Govt schemes agent not yet implemented. "
            "Requires scheme document corpus and vector index.",
        }
        return state
