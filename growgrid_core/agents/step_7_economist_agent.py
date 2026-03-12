"""Agent 7 — Economist Agent.

Computes CAPEX/OPEX per acre/total, revenue/profit ranges,
break-even months, ROI bands, and sensitivity analysis.
Fully deterministic — no LLM calls.

DB tables used:
    - crop_cost_profile (per-crop cost components)
    - practice_cost_profile (per-practice cost components, fallback)
    - yield_baseline_bands (low/base/high yield per acre)
    - price_baseline_bands (low/base/high farmgate price)
    - loss_factor_reference (post-harvest loss % by perishability)
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import (
    get_crop_by_id,
    get_crop_costs,
    get_loss_factor,
    get_practice_costs,
    get_price_bands,
    get_yield_bands,
)
from growgrid_core.utils.types import (
    CostBreakdown,
    CropPortfolioEntry,
    EconomicsReport,
    PlanRequest,
    PracticeScore,
    ROISummary,
    SensitivityResult,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)


class EconomistAgent(BaseAgent):
    """Compute economics: cost breakdown, ROI, sensitivity."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]

        land = profile.land_area_acres
        horizon_months = profile.horizon_months
        horizon_years = max(horizon_months / 12, 1)

        # ── 1. Cost breakdown per crop ──────────────────────────────────
        cost_breakdowns: list[CostBreakdown] = []
        crops_with_data = 0

        # Get practice-level costs as fallback
        practice_costs = get_practice_costs(conn, practice.practice_code)
        practice_capex = sum(
            (r.get("min_inr_per_acre", 0) or 0) + (r.get("max_inr_per_acre", 0) or 0)
            for r in practice_costs
            if r.get("cost_type") == "CAPEX"
        )
        practice_opex = sum(
            (r.get("min_inr_per_acre", 0) or 0) + (r.get("max_inr_per_acre", 0) or 0)
            for r in practice_costs
            if r.get("cost_type") == "OPEX"
        )
        # Average of min+max
        practice_capex_avg = practice_capex / 2 if practice_capex else 0
        practice_opex_avg = practice_opex / 2 if practice_opex else 0

        for entry in portfolio:
            crop_costs = get_crop_costs(conn, entry.crop_id)
            area = land * entry.area_fraction

            if crop_costs:
                crops_with_data += 1
                capex_per_acre = sum(
                    ((r.get("min_inr_per_acre") or 0) + (r.get("max_inr_per_acre") or 0)) / 2
                    for r in crop_costs
                    if r.get("cost_type") == "CAPEX"
                )
                opex_per_acre = sum(
                    ((r.get("min_inr_per_acre") or 0) + (r.get("max_inr_per_acre") or 0)) / 2
                    for r in crop_costs
                    if r.get("cost_type") == "OPEX"
                )
                components = [
                    {
                        "component": r["component"],
                        "cost_type": r["cost_type"],
                        "avg_inr_per_acre": ((r.get("min_inr_per_acre") or 0) + (r.get("max_inr_per_acre") or 0)) / 2,
                    }
                    for r in crop_costs
                ]
            else:
                # Fallback to practice-level averages
                capex_per_acre = practice_capex_avg
                opex_per_acre = practice_opex_avg
                components = [{"component": "estimated_from_practice", "cost_type": "MIXED", "avg_inr_per_acre": capex_per_acre + opex_per_acre}]

            total_cost = (capex_per_acre + opex_per_acre) * area
            cost_breakdowns.append(CostBreakdown(
                crop_id=entry.crop_id,
                crop_name=entry.crop_name,
                capex_per_acre=round(capex_per_acre, 0),
                opex_per_acre=round(opex_per_acre, 0),
                total_cost=round(total_cost, 0),
                components=components,
            ))

        total_capex = sum(cb.capex_per_acre * land * pe.area_fraction for cb, pe in zip(cost_breakdowns, portfolio))
        annual_opex = sum(cb.opex_per_acre * land * pe.area_fraction for cb, pe in zip(cost_breakdowns, portfolio))
        total_opex = annual_opex * horizon_years

        # ── 2. Revenue and ROI per scenario ─────────────────────────────
        roi_summaries: list[ROISummary] = []

        for scenario, yield_key, price_key, loss_key in [
            ("best", "high_yield_per_acre", "high_price_per_unit", "loss_pct_low"),
            ("base", "base_yield_per_acre", "base_price_per_unit", "loss_pct_base"),
            ("worst", "low_yield_per_acre", "low_price_per_unit", "loss_pct_high"),
        ]:
            annual_revenue = 0.0
            total_cost = total_capex + total_opex

            for entry in portfolio:
                area = land * entry.area_fraction
                yield_data = get_yield_bands(conn, entry.crop_id)
                price_data = get_price_bands(conn, entry.crop_id)
                crop_info = get_crop_by_id(conn, entry.crop_id)
                perishability = crop_info.get("perishability", "MED") if crop_info else "MED"
                loss_data = get_loss_factor(conn, perishability)

                if yield_data and price_data:
                    yield_val = yield_data.get(yield_key, 0) or 0
                    price_val = price_data.get(price_key, 0) or 0
                    loss_pct = (loss_data.get(loss_key, 10) or 10) / 100 if loss_data else 0.10
                    revenue = yield_val * price_val * (1 - loss_pct) * area
                    annual_revenue += revenue
                else:
                    logger.warning("Missing yield/price data for %s — revenue set to 0", entry.crop_id)

            # Project annual revenue over the full time horizon
            total_revenue = annual_revenue * horizon_years

            profit = total_revenue - total_cost
            roi_pct = (profit / total_cost * 100) if total_cost > 0 else 0

            # Break-even: months to recover CAPEX from net monthly income
            breakeven = None
            monthly_net_income = (annual_revenue - annual_opex) / 12
            if monthly_net_income > 0:
                breakeven = round(total_capex / monthly_net_income, 1)

            roi_summaries.append(ROISummary(
                scenario=scenario,
                revenue=round(total_revenue, 0),
                total_cost=round(total_cost, 0),
                profit=round(profit, 0),
                roi_pct=round(roi_pct, 1),
                breakeven_months=breakeven,
            ))

        # ── 3. Sensitivity analysis ─────────────────────────────────────
        base_roi = next((r for r in roi_summaries if r.scenario == "base"), None)
        sensitivities: list[SensitivityResult] = []

        if base_roi and base_roi.revenue > 0:
            base_revenue = base_roi.revenue
            base_cost = base_roi.total_cost

            # Price drop -15%
            adj_revenue = base_revenue * 0.85
            adj_profit = adj_revenue - base_cost
            adj_roi = (adj_profit / base_cost * 100) if base_cost > 0 else 0
            sensitivities.append(SensitivityResult(
                factor="price_-15%",
                adjusted_roi_pct=round(adj_roi, 1),
                still_profitable=adj_profit > 0,
            ))

            # Yield drop -10%
            adj_revenue = base_revenue * 0.90
            adj_profit = adj_revenue - base_cost
            adj_roi = (adj_profit / base_cost * 100) if base_cost > 0 else 0
            sensitivities.append(SensitivityResult(
                factor="yield_-10%",
                adjusted_roi_pct=round(adj_roi, 1),
                still_profitable=adj_profit > 0,
            ))

            # Labour cost +10% (affects OPEX portion)
            adj_cost = total_capex + total_opex * 1.10
            adj_profit = base_revenue - adj_cost
            adj_roi = (adj_profit / adj_cost * 100) if adj_cost > 0 else 0
            sensitivities.append(SensitivityResult(
                factor="labour_+10%",
                adjusted_roi_pct=round(adj_roi, 1),
                still_profitable=adj_profit > 0,
            ))

        # ── 4. Assemble report ──────────────────────────────────────────
        data_coverage = crops_with_data / len(portfolio) if portfolio else 0

        economics = EconomicsReport(
            cost_breakdown=cost_breakdowns,
            roi_summary=roi_summaries,
            sensitivity=sensitivities,
            total_capex=round(total_capex, 0),
            total_opex=round(total_opex, 0),
            data_coverage=round(data_coverage, 2),
        )

        state["economics"] = economics
        logger.info(
            "EconomistAgent: %d crops analysed (%.0f%% data coverage), base ROI=%.1f%%.",
            len(portfolio),
            data_coverage * 100,
            roi_summaries[1].roi_pct if len(roi_summaries) > 1 else 0,
        )
        return state
