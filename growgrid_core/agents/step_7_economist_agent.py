"""Agent 7 — Economist Agent (v2).

Professional-grade economic analysis with live price verification,
3-scenario P&L, monthly cashflow, and data quality tracking.

Core rule: All financial numbers from DB + deterministic logic.
LLM is used ONLY for narrative text generation — never for numbers.

DB tables used:
    - crop_cost_profile (per-crop cost components)
    - practice_cost_profile (per-practice cost components, fallback)
    - practice_infrastructure_requirement (infrastructure needs)
    - yield_baseline_bands (low/base/high yield per acre)
    - price_baseline_bands (low/base/high farmgate price)
    - loss_factor_reference (post-harvest loss % by perishability)
    - crop_master (labour need, perishability)
    - practice_master (practice details)
"""

from __future__ import annotations

import logging
import math
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.agents.economist_calculations import (
    _average_time_to_income_months,
    _crop_cycles_per_year,
    _is_long_gestation_crop,
    _scenario_reference,
    compute_crop_economics,
)
from growgrid_core.agents.utils.mandi_price_fetcher import (
    fetch_mandi_prices,
    merge_prices,
)
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import (
    get_crop_by_id,
    get_loss_factor,
    get_price_bands,
    get_yield_bands,
)
from growgrid_core.tools.datagov_client import BaseDataGovMandiClient
from growgrid_core.tools.llm_client import BaseLLMClient
from growgrid_core.tools.tavily_client import BaseTavilyClient
from growgrid_core.tools.tool_cache import ToolCache
from growgrid_core.utils.types import (
    CostBreakdown,
    CropPortfolioEntry,
    CropScenarioResult,
    DataQualityReport,
    EconomicsReport,
    EconomistOutput,
    MonthlyCashflow,
    PlanRequest,
    PracticeScore,
    PriceSource,
    ROISummary,
    ScenarioPnL,
    SensitivityResult,
    SensitivityRow,
    ValidatedProfile,
    WorkingCapitalGap,
)

logger = logging.getLogger(__name__)

# ── Narration prompt (LLM writes prose, never numbers) ──────────────────

_NARRATION_SYSTEM_PROMPT = """\
You are an agricultural finance advisor writing a brief financial narrative \
for an Indian farmer's crop plan.

You will receive pre-computed financial data (scenarios, cashflow, sensitivity). \
Your job is to summarize the financial picture in 3-5 sentences of plain language \
that a farmer or rural banker can understand.

Rules:
- Reference the numbers provided — do NOT invent or recalculate any figures
- Mention the base-case ROI, break-even timeline, and any key risks
- If working capital gap exists, mention it
- Keep the tone practical, not promotional
- Write in English, but use INR amounts with ₹ symbol
- Do NOT use markdown formatting — plain text only
"""

# ── Scenario mapping ─────────────────────────────────────────────────────

# Maps our scenario names to DB yield/price/loss band keys
_SCENARIO_DB_KEYS: dict[str, dict[str, str]] = {
    "conservative": {
        "yield": "low_yield_per_acre",
        "price": "low_price_per_unit",
        "loss": "loss_pct_high",
    },
    "base": {
        "yield": "base_yield_per_acre",
        "price": "base_price_per_unit",
        "loss": "loss_pct_base",
    },
    "optimistic": {
        "yield": "high_yield_per_acre",
        "price": "high_price_per_unit",
        "loss": "loss_pct_low",
    },
}

# Cost multipliers for scenarios (conservative pays more, optimistic less)
_SCENARIO_COST_MULT: dict[str, float] = {
    "conservative": 1.10,
    "base": 1.00,
    "optimistic": 0.95,
}


def _fmt(val: float) -> str:
    """Format INR amount for display."""
    if val >= 1_00_00_000:
        return f"₹{val / 1_00_00_000:.2f} Cr"
    if val >= 1_00_000:
        return f"₹{val / 1_00_000:.2f} L"
    return f"₹{val:,.0f}"


class EconomistAgent(BaseAgent):
    """Compute economics: 3-scenario P&L, cashflow, sensitivity, narration."""

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        llm_client: BaseLLMClient | None = None,
        tavily_client: BaseTavilyClient | None = None,
        cache: ToolCache | None = None,
        datagov_client: BaseDataGovMandiClient | None = None,
    ) -> None:
        self._conn = conn
        self._llm = llm_client
        self._tavily = tavily_client
        self._cache = cache
        self._datagov = datagov_client

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]

        # Use verified portfolio if available, else selected
        verification = state.get("agronomist_verification")
        verified_portfolio = (
            getattr(verification, "verified_crop_portfolio", None)
            if verification
            else None
        )
        portfolio: list[CropPortfolioEntry] = (
            list(verified_portfolio) if verified_portfolio else state["selected_crop_portfolio"]
        )

        land = profile.land_area_acres
        horizon_months = profile.horizon_months
        planning_month = getattr(profile, "planning_month", None)
        labour = (
            profile.labour_availability.value
            if hasattr(profile.labour_availability, "value")
            else str(profile.labour_availability)
        )
        irrigation = (
            profile.irrigation_source.value
            if hasattr(profile.irrigation_source, "value")
            else str(profile.irrigation_source)
        )
        water = (
            profile.water_availability.value
            if hasattr(profile.water_availability, "value")
            else str(profile.water_availability)
        )
        budget = (
            profile.budget_total_inr
            if hasattr(profile, "budget_total_inr")
            else request.budget_total_inr
        )

        # Extract state name from location (e.g. "Maharashtra, Pune" → "Maharashtra")
        location = profile.location or request.location or ""
        state_name = location.split(",")[0].strip() if location else ""

        portfolio_dicts = [
            {
                "crop_id": e.crop_id,
                "crop_name": e.crop_name,
                "area_fraction": e.area_fraction,
            }
            for e in portfolio
        ]

        # ════════════════════════════════════════════════════════════════
        # STEP 1 — Load base economics from DB
        # ════════════════════════════════════════════════════════════════
        scenario_ref = _scenario_reference(conn, practice.practice_code)
        crop_economics_list = []
        crop_metadata: dict[str, dict[str, Any]] = {}  # crop_id → collected data

        for entry in portfolio_dicts:
            area = land * entry["area_fraction"]
            ce = compute_crop_economics(
                conn=conn,
                crop_id=entry["crop_id"],
                crop_name=entry["crop_name"],
                area_acres=area,
                area_fraction=entry["area_fraction"],
                practice_code=practice.practice_code,
                labour_availability=labour,
                irrigation_source=irrigation,
                water_availability=water,
                land_total_acres=land,
                horizon_months=horizon_months,
                planning_month=planning_month,
                capital_buffer_floor_months=scenario_ref["capital_buffer_floor_months"],
                capex_contingency_pct=scenario_ref["capex_contingency_pct"],
                llm_client=self._llm,
            )
            crop_economics_list.append(ce)

            # Collect metadata for revenue computation
            crop_info = get_crop_by_id(conn, entry["crop_id"])
            yield_bands = get_yield_bands(conn, entry["crop_id"])
            db_price_bands = get_price_bands(conn, entry["crop_id"])
            perishability = (crop_info or {}).get("perishability", "MED")
            loss_factor = get_loss_factor(conn, perishability)

            crop_metadata[entry["crop_id"]] = {
                "crop_info": crop_info,
                "crop_name": entry["crop_name"],
                "area_fraction": entry["area_fraction"],
                "area_acres": area,
                "yield_bands": yield_bands or {},
                "db_price_bands": db_price_bands or {},
                "loss_factor": loss_factor or {},
                "has_db_data": ce.has_db_data,
                "used_llm_estimate": ce.used_llm_estimate,
                "capex_per_acre": ce.capex_per_acre,
                "opex_per_acre": ce.opex_per_acre,
                "total_setup_capex": ce.total_setup_capex,
                "total_opex_annual": ce.total_opex_annual,
                "first_income_months": ce.first_income_months,
                "season_start_delay": ce.season_start_delay_months,
                "components": ce.components,
            }

        # Aggregate totals
        total_capex = sum(ce.total_capex for ce in crop_economics_list)
        total_annual_opex = sum(ce.total_opex_annual for ce in crop_economics_list)
        total_opex_horizon = sum(ce.total_opex_horizon for ce in crop_economics_list)
        crops_with_data = sum(1 for ce in crop_economics_list if ce.has_db_data)
        data_coverage = crops_with_data / len(portfolio_dicts) if portfolio_dicts else 0

        # ════════════════════════════════════════════════════════════════
        # STEP 2 — Fetch live mandi prices and merge with DB
        # ════════════════════════════════════════════════════════════════
        price_sources: list[PriceSource] = []
        merged_prices: dict[str, dict[str, Any]] = {}  # crop_id → merged price dict
        fields_from_live: list[str] = []
        fields_from_db: list[str] = []
        fields_from_fallback: list[str] = []

        for crop_id, meta in crop_metadata.items():
            mandi_result = fetch_mandi_prices(
                tavily=self._tavily,
                llm_client=self._llm,
                cache=self._cache,
                crop_name=meta["crop_name"],
                state=state_name,
                datagov_client=self._datagov,
            )

            merged = merge_prices(meta["db_price_bands"], mandi_result)
            merged_prices[crop_id] = merged

            price_sources.append(
                PriceSource(
                    crop=meta["crop_name"],
                    source=merged["source"],
                    confidence=merged["confidence"],
                    fetch_date=mandi_result.fetch_date,
                    price_min=merged.get("price_min"),
                    price_max=merged.get("price_max"),
                )
            )

            if merged["source"] == "live_fetch":
                fields_from_live.append(f"{meta['crop_name']} price")
            elif merged["source"] == "database":
                fields_from_db.append(f"{meta['crop_name']} price")
            else:
                fields_from_fallback.append(f"{meta['crop_name']} price")

        # Track data quality for cost fields
        for crop_id, meta in crop_metadata.items():
            if meta["has_db_data"]:
                fields_from_db.append(f"{meta['crop_name']} costs")
            elif meta["used_llm_estimate"]:
                fields_from_fallback.append(f"{meta['crop_name']} costs")
            else:
                fields_from_db.append(f"{meta['crop_name']} costs (practice-level)")

        # ════════════════════════════════════════════════════════════════
        # STEP 3 — Compute 3 scenarios (pure arithmetic)
        # ════════════════════════════════════════════════════════════════
        horizon_years = max(horizon_months / 12, 1)
        scenarios: dict[str, ScenarioPnL] = {}

        for scenario_name in ("conservative", "base", "optimistic"):
            db_keys = _SCENARIO_DB_KEYS[scenario_name]
            cost_mult = _SCENARIO_COST_MULT[scenario_name]
            crop_results: list[CropScenarioResult] = []
            scenario_total_revenue = 0.0
            scenario_total_setup = 0.0
            scenario_total_opex = 0.0

            for crop_id, meta in crop_metadata.items():
                area = meta["area_acres"]
                if area <= 0:
                    continue

                # Yield from DB bands
                yield_val = float(meta["yield_bands"].get(db_keys["yield"], 0) or 0)

                # Price from merged prices (scenario-adjusted)
                mp = merged_prices[crop_id]
                p_min = float(mp.get("price_min", 0) or 0)
                p_max = float(mp.get("price_max", 0) or 0)
                p_base = float(mp.get("price_base", 0) or 0)
                if scenario_name == "conservative":
                    price_val = p_min if p_min > 0 else p_base
                elif scenario_name == "optimistic":
                    price_val = p_max if p_max > 0 else p_base
                else:
                    price_val = p_base

                # Loss from DB
                loss_pct = float(meta["loss_factor"].get(db_keys["loss"], 10) or 10) / 100

                # Costs (from compute_crop_economics, scenario-adjusted)
                setup_cost_per_acre = meta["capex_per_acre"]
                operating_cost_per_acre = meta["opex_per_acre"] * cost_mult

                # Revenue per harvest cycle
                gross_revenue_per_acre = yield_val * price_val * (1 - loss_pct)

                # Annualize revenue based on crop cycles
                crop_info = meta["crop_info"]
                cycles = _crop_cycles_per_year(crop_info)
                annual_revenue_per_acre = gross_revenue_per_acre * cycles

                # Adjust for bearing fraction in long-gestation crops
                if _is_long_gestation_crop(crop_info):
                    avg_gestation = _average_time_to_income_months(crop_info)
                    if horizon_months > avg_gestation:
                        bearing_months = horizon_months - avg_gestation
                        bearing_fraction = bearing_months / horizon_months
                    else:
                        bearing_fraction = 0.0
                    annual_revenue_per_acre *= bearing_fraction

                net_profit_per_acre = annual_revenue_per_acre - operating_cost_per_acre
                total_crop_revenue = annual_revenue_per_acre * area * horizon_years
                total_crop_setup = setup_cost_per_acre * area
                total_crop_opex = operating_cost_per_acre * area * horizon_years

                scenario_total_revenue += total_crop_revenue
                scenario_total_setup += total_crop_setup
                scenario_total_opex += total_crop_opex

                crop_results.append(
                    CropScenarioResult(
                        crop_id=crop_id,
                        crop_name=meta["crop_name"],
                        area_acres=round(area, 2),
                        setup_cost_per_acre=round(setup_cost_per_acre, 0),
                        operating_cost_per_acre=round(operating_cost_per_acre, 0),
                        gross_revenue_per_acre=round(annual_revenue_per_acre, 0),
                        net_profit_per_acre=round(net_profit_per_acre, 0),
                        yield_per_acre=round(yield_val, 2),
                        price_per_unit=round(price_val, 2),
                        loss_pct=round(loss_pct * 100, 1),
                    )
                )

            total_cost = scenario_total_setup + scenario_total_opex
            total_profit = scenario_total_revenue - total_cost
            roi_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0.0

            # Break-even for this scenario
            be_months, be_years, be_status = _compute_break_even(
                total_setup=scenario_total_setup,
                annual_opex=scenario_total_opex / horizon_years if horizon_years > 0 else 0,
                annual_revenue=scenario_total_revenue / horizon_years if horizon_years > 0 else 0,
                horizon_months=horizon_months,
            )

            scenarios[scenario_name] = ScenarioPnL(
                scenario=scenario_name,
                crops=crop_results,
                total_setup_cost=round(scenario_total_setup, 0),
                total_operating_cost=round(scenario_total_opex, 0),
                total_revenue=round(scenario_total_revenue, 0),
                total_profit=round(total_profit, 0),
                roi_percent=round(roi_pct, 1),
                break_even_months=be_months,
                break_even_years=be_years,
                break_even_status=be_status,
            )

        # ════════════════════════════════════════════════════════════════
        # STEP 4 — Monthly cashflow (Year 1, base scenario)
        # ════════════════════════════════════════════════════════════════
        base_pnl = scenarios.get("base")
        monthly_cashflow: list[MonthlyCashflow] = []
        cumulative = 0.0

        if base_pnl and base_pnl.total_revenue > 0:
            monthly_setup = base_pnl.total_setup_cost  # all setup in month 1
            monthly_opex = base_pnl.total_operating_cost / horizon_years / 12
            annual_revenue = base_pnl.total_revenue / horizon_years

            for month in range(1, 13):
                expense = monthly_opex
                if month == 1:
                    expense += monthly_setup

                # Revenue starts after weighted average time_to_income
                avg_first_income = 0.0
                total_frac = 0.0
                for meta in crop_metadata.values():
                    frac = meta["area_fraction"]
                    first_inc = meta["first_income_months"] + meta["season_start_delay"]
                    avg_first_income += first_inc * frac
                    total_frac += frac
                if total_frac > 0:
                    avg_first_income /= total_frac

                if month > avg_first_income:
                    active_months = 12 - math.ceil(avg_first_income)
                    rev = annual_revenue / max(active_months, 1)
                else:
                    rev = 0.0

                net = rev - expense
                cumulative += net

                monthly_cashflow.append(
                    MonthlyCashflow(
                        month=month,
                        operating_expense=round(expense, 0),
                        revenue=round(rev, 0),
                        net_cash=round(net, 0),
                        cumulative_position=round(cumulative, 0),
                    )
                )
        else:
            # No revenue data — produce zero cashflow
            for month in range(1, 13):
                monthly_cashflow.append(
                    MonthlyCashflow(month=month)
                )

        # ════════════════════════════════════════════════════════════════
        # STEP 5 — Working capital gap
        # ════════════════════════════════════════════════════════════════
        negative_months = [
            mc.month for mc in monthly_cashflow if mc.cumulative_position < 0
        ]
        min_cumulative = min(
            (mc.cumulative_position for mc in monthly_cashflow),
            default=0.0,
        )
        working_capital_gap = WorkingCapitalGap(
            exists=len(negative_months) > 0,
            amount=round(abs(min_cumulative), 0) if min_cumulative < 0 else 0.0,
            months=negative_months,
        )

        # ════════════════════════════════════════════════════════════════
        # STEP 6 — Break-even summary (already computed per scenario)
        # ════════════════════════════════════════════════════════════════
        break_even_summary: dict[str, Any] = {}
        for sc_name, sc_pnl in scenarios.items():
            break_even_summary[sc_name] = {
                "months": sc_pnl.break_even_months,
                "years": sc_pnl.break_even_years,
                "status": sc_pnl.break_even_status,
            }

        # ════════════════════════════════════════════════════════════════
        # STEP 7 — Sensitivity analysis (5 shocks on base scenario)
        # ════════════════════════════════════════════════════════════════
        sensitivity_rows: list[SensitivityRow] = []

        if base_pnl and base_pnl.total_revenue > 0:
            base_rev = base_pnl.total_revenue

            shocks = [
                ("price_drop_20%", "Market price drops 20%", 0.80, 1.0),
                ("price_drop_40%", "Market price drops 40%", 0.60, 1.0),
                ("yield_drop_20%", "Yield drops 20% due to weather/pest stress", 0.80, 1.0),
                ("labour_cost_up_20%", "Labour costs increase 20%", 1.0, 1.20),
                ("input_cost_up_15%", "Input/material costs increase 15%", 1.0, 1.15),
            ]

            for factor, desc, rev_mult, cost_mult in shocks:
                adj_rev = base_rev * rev_mult
                adj_opex = base_pnl.total_operating_cost * cost_mult
                adj_cost = base_pnl.total_setup_cost + adj_opex
                adj_profit = adj_rev - adj_cost
                adj_roi = (adj_profit / adj_cost * 100) if adj_cost > 0 else 0.0

                sensitivity_rows.append(
                    SensitivityRow(
                        factor=factor,
                        description=desc,
                        adjusted_revenue=round(adj_rev, 0),
                        adjusted_cost=round(adj_cost, 0),
                        adjusted_profit=round(adj_profit, 0),
                        adjusted_roi_percent=round(adj_roi, 1),
                        still_profitable=adj_profit > 0,
                    )
                )

        # ════════════════════════════════════════════════════════════════
        # STEP 8 — LLM narration (ONLY LLM usage — never for numbers)
        # ════════════════════════════════════════════════════════════════
        financial_narrative = self._generate_narration(
            scenarios=scenarios,
            working_capital_gap=working_capital_gap,
            sensitivity_rows=sensitivity_rows,
            horizon_months=horizon_months,
        )

        # ════════════════════════════════════════════════════════════════
        # STEP 9 — Assemble output
        # ════════════════════════════════════════════════════════════════

        # Data quality report
        if fields_from_fallback:
            overall_quality = "LOW"
            lowest_conf_note = f"Fallback used for: {', '.join(fields_from_fallback)}"
        elif data_coverage < 0.7 or not fields_from_live:
            overall_quality = "MED"
            lowest_conf_note = "All data from database (no live price verification)"
        else:
            overall_quality = "HIGH"
            lowest_conf_note = "All data from database or live fetch"

        data_quality = DataQualityReport(
            overall_quality=overall_quality,
            fields_from_live_fetch=fields_from_live,
            fields_from_database=fields_from_db,
            fields_from_fallback=fields_from_fallback,
            lowest_confidence_assumption=lowest_conf_note,
        )

        # Build assumptions
        assumptions = self._build_assumptions(
            land=land,
            horizon_months=horizon_months,
            labour=labour,
            irrigation=irrigation,
            water=water,
            practice=practice.practice_code,
            price_sources=price_sources,
            data_coverage=data_coverage,
        )

        # Build warnings
        warnings = self._build_warnings(
            scenarios=scenarios,
            sensitivity_rows=sensitivity_rows,
            budget=budget,
            data_coverage=data_coverage,
            working_capital_gap=working_capital_gap,
        )

        # Primary output — EconomistOutput
        economist_output = EconomistOutput(
            scenarios=scenarios,
            monthly_cashflow_year1=monthly_cashflow,
            working_capital_gap=working_capital_gap,
            sensitivity_analysis=sensitivity_rows,
            break_even=break_even_summary,
            financial_narrative=financial_narrative,
            data_quality_summary=data_quality,
            price_sources=price_sources,
            assumptions_used=assumptions,
            warnings=warnings,
        )

        # Backward-compatible EconomicsReport (for existing frontend)
        cost_breakdowns = [
            CostBreakdown(
                crop_id=ce.crop_id,
                crop_name=ce.crop_name,
                capex_per_acre=ce.capex_per_acre,
                opex_per_acre=ce.opex_per_acre,
                total_cost=ce.total_setup_capex + ce.total_opex_annual,
                components=ce.components,
            )
            for ce in crop_economics_list
        ]

        # Map to old-style ROI summaries
        roi_summaries = []
        old_scenario_map = {
            "optimistic": "best",
            "base": "base",
            "conservative": "worst",
        }
        for sc_name, sc_pnl in scenarios.items():
            roi_summaries.append(
                ROISummary(
                    scenario=old_scenario_map.get(sc_name, sc_name),
                    revenue=sc_pnl.total_revenue,
                    total_cost=sc_pnl.total_setup_cost + sc_pnl.total_operating_cost,
                    profit=sc_pnl.total_profit,
                    roi_pct=sc_pnl.roi_percent,
                    annualized_roi_pct=sc_pnl.roi_percent / horizon_years if horizon_years > 0 else 0,
                    capital_required=sc_pnl.total_setup_cost,
                    peak_cash_deficit=working_capital_gap.amount if working_capital_gap.exists else 0,
                    payback_status=sc_pnl.break_even_status,
                    breakeven_months=sc_pnl.break_even_months,
                )
            )

        # Map to old-style sensitivity
        old_sensitivities = [
            SensitivityResult(
                factor=sr.factor,
                description=sr.description,
                adjusted_roi_pct=sr.adjusted_roi_percent,
                adjusted_revenue=sr.adjusted_revenue,
                adjusted_cost=sr.adjusted_cost,
                adjusted_profit=sr.adjusted_profit,
                still_profitable=sr.still_profitable,
            )
            for sr in sensitivity_rows
        ]

        # Revenue/profit/break-even summaries for backward compat
        base_sc = scenarios.get("base")
        opt_sc = scenarios.get("optimistic")
        con_sc = scenarios.get("conservative")
        revenue_summary = {
            "best_annual": (opt_sc.total_revenue / horizon_years) if opt_sc else 0,
            "base_annual": (base_sc.total_revenue / horizon_years) if base_sc else 0,
            "worst_annual": (con_sc.total_revenue / horizon_years) if con_sc else 0,
            "best_total": opt_sc.total_revenue if opt_sc else 0,
            "base_total": base_sc.total_revenue if base_sc else 0,
            "worst_total": con_sc.total_revenue if con_sc else 0,
        }
        profit_summary = {
            "best": opt_sc.total_profit if opt_sc else 0,
            "base": base_sc.total_profit if base_sc else 0,
            "worst": con_sc.total_profit if con_sc else 0,
        }
        break_even_compat = {
            "best_months": opt_sc.break_even_months if opt_sc else None,
            "base_months": base_sc.break_even_months if base_sc else None,
            "worst_months": con_sc.break_even_months if con_sc else None,
            "best_status": opt_sc.break_even_status if opt_sc else "NOT_REACHED",
            "base_status": base_sc.break_even_status if base_sc else "NOT_REACHED",
            "worst_status": con_sc.break_even_status if con_sc else "NOT_REACHED",
        }

        economics = EconomicsReport(
            cost_breakdown=cost_breakdowns,
            roi_summary=roi_summaries,
            sensitivity=old_sensitivities,
            total_capex=round(total_capex, 0),
            total_opex=round(total_opex_horizon, 0),
            total_annual_opex=round(total_annual_opex, 0),
            data_coverage=round(data_coverage, 2),
            revenue_summary=revenue_summary,
            profit_summary=profit_summary,
            break_even=break_even_compat,
            assumptions_used=assumptions,
            warnings=warnings,
            graph_payload=self._build_graph_payload(scenarios, monthly_cashflow),
            ui_payload=self._build_ui_payload(economist_output),
        )

        state["economics"] = economics
        state["economist_output"] = economist_output

        base_roi = base_sc.roi_percent if base_sc else 0
        logger.info(
            "EconomistAgent: %d crops analysed (%.0f%% data coverage), "
            "base ROI=%.1f%%, %d live price(s).",
            len(portfolio),
            data_coverage * 100,
            base_roi,
            len(fields_from_live),
        )
        return state

    # ── Helper methods ─────────────────────────────────────────────────

    def _generate_narration(
        self,
        *,
        scenarios: dict[str, ScenarioPnL],
        working_capital_gap: WorkingCapitalGap,
        sensitivity_rows: list[SensitivityRow],
        horizon_months: int,
    ) -> str | None:
        """Generate financial narrative via LLM. Returns None if LLM unavailable."""
        if self._llm is None:
            return None

        base = scenarios.get("base")
        if not base or base.total_revenue <= 0:
            return None

        con = scenarios.get("conservative")
        opt = scenarios.get("optimistic")

        unprofitable_shocks = sum(1 for s in sensitivity_rows if not s.still_profitable)

        data_summary = (
            f"Base scenario: Revenue {_fmt(base.total_revenue)}, "
            f"Cost {_fmt(base.total_setup_cost + base.total_operating_cost)}, "
            f"Profit {_fmt(base.total_profit)}, ROI {base.roi_percent:.1f}%. "
            f"Break-even: {base.break_even_status}"
            + (f" at {base.break_even_months:.0f} months" if base.break_even_months else "")
            + ". "
            f"Conservative profit: {_fmt(con.total_profit) if con else 'N/A'}. "
            f"Optimistic profit: {_fmt(opt.total_profit) if opt else 'N/A'}. "
            f"Planning horizon: {horizon_months} months. "
        )
        if working_capital_gap.exists:
            data_summary += (
                f"Working capital gap: {_fmt(working_capital_gap.amount)} "
                f"in months {working_capital_gap.months}. "
            )
        data_summary += (
            f"{unprofitable_shocks} of {len(sensitivity_rows)} sensitivity "
            f"scenarios turn loss-making."
        )

        try:
            result = self._llm.complete_text(
                _NARRATION_SYSTEM_PROMPT,
                data_summary,
            )
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.warning("LLM narration failed: %s", e)
            return None

    def _build_assumptions(
        self,
        *,
        land: float,
        horizon_months: int,
        labour: str,
        irrigation: str,
        water: str,
        practice: str,
        price_sources: list[PriceSource],
        data_coverage: float,
    ) -> list[str]:
        assumptions = [
            f"Land area: {land} acres",
            f"Planning horizon: {horizon_months} months ({horizon_months / 12:.1f} years)",
            f"Labour availability: {labour}",
            f"Irrigation source: {irrigation}",
            f"Water availability: {water}",
            f"Farming practice: {practice}",
            "All financial calculations are deterministic — LLM is used only for narrative text",
            "Crop costs from knowledge base, blended with practice-level profiles for missing components",
            "3 scenarios: conservative (low yield/price, high loss/cost), base (mid), optimistic (high yield/price, low loss/cost)",
        ]

        live_prices = [ps for ps in price_sources if ps.source == "live_fetch"]
        if live_prices:
            assumptions.append(
                f"Live mandi prices used for {len(live_prices)} crop(s): "
                + ", ".join(ps.crop for ps in live_prices)
            )
        else:
            assumptions.append("All prices from database baseline bands (no live fetch available)")

        assumptions.append(
            f"Data coverage: {data_coverage * 100:.0f}% of crops have crop-level cost data"
        )

        return assumptions

    def _build_warnings(
        self,
        *,
        scenarios: dict[str, ScenarioPnL],
        sensitivity_rows: list[SensitivityRow],
        budget: int,
        data_coverage: float,
        working_capital_gap: WorkingCapitalGap,
    ) -> list[str]:
        warnings: list[str] = []
        base = scenarios.get("base")
        con = scenarios.get("conservative")

        if base and base.roi_percent < 0:
            warnings.append(
                "Base scenario shows negative ROI. Review crop mix, area, or investment intensity."
            )
        if con and con.total_profit < 0:
            warnings.append(
                "Conservative scenario results in a loss. Plan for price, yield, and cost shocks."
            )
        if base and base.break_even_status == "NOT_REACHED":
            warnings.append(
                "Break-even not reached within the planning horizon under base assumptions."
            )
        if working_capital_gap.exists:
            warnings.append(
                f"Working capital gap of {_fmt(working_capital_gap.amount)} exists "
                f"in months {working_capital_gap.months}. Arrange bridge funding or phased deployment."
            )
        if budget > 0 and base:
            total_base_cost = base.total_setup_cost + base.total_operating_cost
            if total_base_cost > budget:
                warnings.append(
                    f"Base-case total cost ({_fmt(total_base_cost)}) exceeds stated budget "
                    f"({_fmt(float(budget))}). Additional financing may be needed."
                )

        if data_coverage < 0.5:
            warnings.append(
                f"Only {data_coverage * 100:.0f}% of crops have detailed cost data. "
                "Practice-level estimates may reduce accuracy."
            )

        unprofitable = [s for s in sensitivity_rows if not s.still_profitable]
        if len(unprofitable) >= 3:
            warnings.append(
                f"{len(unprofitable)} of {len(sensitivity_rows)} sensitivity scenarios "
                "turn loss-making. This plan has limited financial resilience."
            )

        return warnings

    def _build_graph_payload(
        self,
        scenarios: dict[str, ScenarioPnL],
        cashflow: list[MonthlyCashflow],
    ) -> dict[str, Any]:
        """Build chart data for frontend visualization."""
        scenario_chart = []
        for sc_name in ("conservative", "base", "optimistic"):
            sc = scenarios.get(sc_name)
            if sc:
                scenario_chart.append({
                    "scenario": sc_name,
                    "revenue": sc.total_revenue,
                    "cost": sc.total_setup_cost + sc.total_operating_cost,
                    "profit": sc.total_profit,
                    "roi_percent": sc.roi_percent,
                })

        cashflow_chart = [
            {
                "month": mc.month,
                "expense": mc.operating_expense,
                "revenue": mc.revenue,
                "net": mc.net_cash,
                "cumulative": mc.cumulative_position,
            }
            for mc in cashflow
        ]

        return {
            "scenario_comparison": scenario_chart,
            "monthly_cashflow": cashflow_chart,
        }

    def _build_ui_payload(
        self,
        output: EconomistOutput,
    ) -> dict[str, Any]:
        """Build structured UI data for frontend rendering."""
        base = output.scenarios.get("base")
        return {
            "headline": {
                "base_roi": base.roi_percent if base else 0,
                "base_profit": base.total_profit if base else 0,
                "break_even_months": base.break_even_months if base else None,
                "break_even_status": base.break_even_status if base else "NOT_REACHED",
                "data_quality": output.data_quality_summary.overall_quality if output.data_quality_summary else "MED",
                "live_price_count": len(output.data_quality_summary.fields_from_live_fetch) if output.data_quality_summary else 0,
            },
            "has_narrative": output.financial_narrative is not None,
            "working_capital_gap": {
                "exists": output.working_capital_gap.exists if output.working_capital_gap else False,
                "amount": output.working_capital_gap.amount if output.working_capital_gap else 0,
            },
        }


def _compute_break_even(
    *,
    total_setup: float,
    annual_opex: float,
    annual_revenue: float,
    horizon_months: int,
) -> tuple[float | None, float | None, str]:
    """Compute break-even month and year.

    Returns (months, years, status) where status is
    "WITHIN_HORIZON", "BEYOND_HORIZON", or "NOT_REACHED".
    """
    if annual_revenue <= 0 or total_setup <= 0:
        return None, None, "NOT_REACHED"

    monthly_revenue = annual_revenue / 12
    monthly_opex = annual_opex / 12
    monthly_net = monthly_revenue - monthly_opex

    if monthly_net <= 0:
        return None, None, "NOT_REACHED"

    # Months to recover setup cost from net monthly income
    months_to_recover = total_setup / monthly_net

    if months_to_recover <= horizon_months:
        return (
            round(months_to_recover, 1),
            round(months_to_recover / 12, 1),
            "WITHIN_HORIZON",
        )

    # Check extended window
    max_months = min(horizon_months * 2, 120)
    if months_to_recover <= max_months:
        return (
            round(months_to_recover, 1),
            round(months_to_recover / 12, 1),
            "BEYOND_HORIZON",
        )

    return None, None, "NOT_REACHED"
