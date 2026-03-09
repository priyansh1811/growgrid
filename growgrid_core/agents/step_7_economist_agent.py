"""Agent 6 — Economist Agent (Phase-1 stub).

Purpose: Compute CAPEX/OPEX per acre/total, revenue/profit ranges,
break-even months, ROI bands, and sensitivity analysis.

DB tables required (not yet populated):
    - input_cost_reference
    - labour_rate_reference
    - crop_cost_profile
    - yield_baseline_bands
    - price_baseline_bands
    - loss_factor_reference
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import PlanRequest

logger = logging.getLogger(__name__)


class EconomistAgent(BaseAgent):
    """Compute economics: cost breakdown, ROI, sensitivity. (Phase-1 stub)"""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        logger.info("EconomistAgent is a Phase-1 stub — returning placeholder.")

        state["economics"] = {
            "status": "stub",
            "cost_breakdown": {
                "capex_per_acre": None,
                "opex_per_acre": None,
                "total_capex": None,
                "total_opex": None,
            },
            "roi_summary": {
                "best_case_roi_pct": None,
                "base_case_roi_pct": None,
                "worst_case_roi_pct": None,
            },
            "breakeven_months": None,
            "sensitivity": {
                "price_minus_15pct": None,
                "yield_minus_10pct": None,
                "labour_plus_10pct": None,
            },
            "message": "Economist agent not yet implemented. "
            "Requires crop_cost_profile and yield/price baseline data.",
        }
        return state
