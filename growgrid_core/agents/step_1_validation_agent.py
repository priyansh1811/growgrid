"""Agent 1 — Validation & Sanity Checker.

Purely deterministic: enforces types/enums, computes derived fields,
emits hard and soft constraints, and produces warnings.
"""

from __future__ import annotations

from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.config import (
    EXTREMELY_LOW_BUDGET_THRESHOLD,
    HORIZON_EXTREME_WARNING_MONTHS,
    HORIZON_SHORT_WARNING_MONTHS,
    INTEGRATED_MIN_LAND_ACRES,
    LARGE_BUDGET_INR,
    LOW_BUDGET_WARNING_THRESHOLD,
    MICRO_PLOT_ACRES,
    ORCHARD_MIN_HORIZON_MONTHS,
    POLYHOUSE_MIN_BUDGET_PER_ACRE,
)
from growgrid_core.utils.enums import IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import (
    HardConstraint,
    PlanRequest,
    SoftConstraint,
    ValidatedProfile,
)


class ValidationAgent(BaseAgent):
    """Validate inputs, compute derived fields, produce constraints/warnings."""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        # PlanRequest already validated by Pydantic (cross-field in model_validator).
        # Here we only do domain-specific rules and derived fields.

        # ── Derived fields & normalized location ───────────────────────
        location = " ".join(request.location.strip().split())  # strip and collapse spaces
        budget_per_acre = request.budget_total_inr / request.land_area_acres
        horizon_months = round(request.time_horizon_years * 12)

        user_context = getattr(request, "user_context", None) or None

        planning_month = getattr(request, "planning_month", None) if request else None
        validated = ValidatedProfile(
            location=location,
            land_area_acres=request.land_area_acres,
            water_availability=request.water_availability,
            irrigation_source=request.irrigation_source,
            budget_total_inr=request.budget_total_inr,
            labour_availability=request.labour_availability,
            goal=request.goal,
            time_horizon_years=request.time_horizon_years,
            risk_tolerance=request.risk_tolerance,
            budget_per_acre=budget_per_acre,
            horizon_months=horizon_months,
            user_context=user_context,
            planning_month=planning_month if 1 <= (planning_month or 0) <= 12 else None,
        )

        # ── Hard constraints ─────────────────────────────────────────
        # Practice/crop agents interpret: exclude_if_equal → drop candidates where attr == threshold;
        # exclude_practice_codes → threshold is comma-separated list of practice codes to exclude.
        hard: list[HardConstraint] = []

        if request.water_availability == WaterLevel.LOW:
            hard.append(
                HardConstraint(
                    dimension="water",
                    operator="exclude_if_equal",
                    threshold="HIGH",
                    reason="User water availability is LOW; exclude practices/crops requiring HIGH water.",
                )
            )

        if request.labour_availability == LabourLevel.LOW:
            hard.append(
                HardConstraint(
                    dimension="labour",
                    operator="exclude_if_equal",
                    threshold="HIGH",
                    reason="User labour availability is LOW; exclude practices/crops requiring HIGH labour.",
                )
            )
            hard.append(
                HardConstraint(
                    dimension="practice",
                    operator="exclude_practice_codes",
                    threshold="POLYHOUSE,NET_HOUSE,HYDROPONICS",
                    reason="Labour availability is LOW; exclude protected cultivation and hydroponics which require high operational labour.",
                )
            )

        if budget_per_acre < POLYHOUSE_MIN_BUDGET_PER_ACRE:
            hard.append(
                HardConstraint(
                    dimension="practice",
                    operator="exclude_practice_codes",
                    threshold="POLYHOUSE,NET_HOUSE,HYDROPONICS",
                    reason=(
                        f"Budget per acre ({budget_per_acre:.0f} INR) is below protected-cultivation threshold "
                        f"({POLYHOUSE_MIN_BUDGET_PER_ACRE:.0f} INR/acre); exclude protected cultivation practices."
                    ),
                )
            )

        if request.risk_tolerance == RiskLevel.LOW:
            hard.append(
                HardConstraint(
                    dimension="risk",
                    operator="exclude_if_equal",
                    threshold="HIGH",
                    reason="User risk tolerance is LOW; exclude HIGH-risk practices/crops.",
                )
            )

        # ── Horizon gate: orchard-only needs patience; allow orchard+intercrop for early cashflow.
        if horizon_months < ORCHARD_MIN_HORIZON_MONTHS:
            hard.append(
                HardConstraint(
                    dimension="practice",
                    operator="exclude_practice_codes",
                    threshold="ORCHARD",
                    reason="Time horizon < 24 months; exclude orchard-only models (orchard+intercrop can still be considered).",
                )
            )

        # Irrigation feasibility: if there is no irrigation source, protected/hydroponics are infeasible.
        if request.irrigation_source == IrrigationSource.NONE:
            hard.append(
                HardConstraint(
                    dimension="practice",
                    operator="exclude_practice_codes",
                    threshold="POLYHOUSE,NET_HOUSE,HYDROPONICS,DRIP_INTENSIVE",
                    reason="No irrigation source selected; exclude protected cultivation, hydroponics, and drip-intensive models.",
                )
            )

        # ── Soft constraints ─────────────────────────────────────────
        soft: list[SoftConstraint] = []

        if request.irrigation_source == IrrigationSource.NONE:
            soft.append(
                SoftConstraint(
                    dimension="irrigation",
                    preference="prefer_rainfed",
                    penalty=0.0,
                    reason="No irrigation source; prefer rain-fed / dryland practices.",
                )
            )

        if request.water_availability == WaterLevel.MED:
            soft.append(
                SoftConstraint(
                    dimension="water",
                    preference="penalise_high_water",
                    penalty=0.15,
                    reason="Moderate water; apply a small penalty to HIGH-water options.",
                )
            )

        # ── Warnings (proceed but expect limitations; shown in UI) ─────
        warnings: list[str] = []

        if request.land_area_acres < MICRO_PLOT_ACRES:
            warnings.append(
                f"Micro-plot detected (< {MICRO_PLOT_ACRES} acres). Practice options may be very limited."
            )
        # Integrated farming systems typically need more space for multiple components.
        if request.land_area_acres < INTEGRATED_MIN_LAND_ACRES:
            hard.append(
                HardConstraint(
                    dimension="practice",
                    operator="exclude_practice_codes",
                    threshold="INTEGRATED",
                    reason="Land area < 0.5 acres; exclude Integrated Farming System due to space constraints for multiple components.",
                )
            )

        if budget_per_acre < LOW_BUDGET_WARNING_THRESHOLD:
            warnings.append(
                f"Very tight budget ({budget_per_acre:.0f} INR/acre). Practice and crop choices will be constrained."
            )
        # Extremely low budget: most intensive models become infeasible.
        if budget_per_acre < EXTREMELY_LOW_BUDGET_THRESHOLD:
            warnings.append(
                f"Extremely low budget ({budget_per_acre:.0f} INR/acre). Only minimal-input models may remain feasible."
            )

        if horizon_months < HORIZON_EXTREME_WARNING_MONTHS:
            warnings.append(
                f"Extremely short horizon (< {HORIZON_EXTREME_WARNING_MONTHS} months). Almost no viable cropping options."
            )
        elif horizon_months < HORIZON_SHORT_WARNING_MONTHS:
            warnings.append(
                f"Very short time horizon (< {HORIZON_SHORT_WARNING_MONTHS} months). Only quick-harvest options will be considered."
            )

        if request.budget_total_inr > LARGE_BUDGET_INR:
            warnings.append(
                f"Very large budget entered (> {LARGE_BUDGET_INR // 10_000_000} crore INR). Please verify the amount."
            )

        # ── Conflicts: logical tensions to confirm (not invalid; shown in UI) ─
        conflicts: list[str] = []
        if request.irrigation_source == IrrigationSource.NONE and request.water_availability == WaterLevel.HIGH:
            conflicts.append(
                "Irrigation source is NONE but water availability is HIGH. Please verify; water availability may be seasonal or based on rainfall."
            )
        if request.water_availability == WaterLevel.LOW and request.irrigation_source in {
            IrrigationSource.DRIP,
            IrrigationSource.BOREWELL,
            IrrigationSource.CANAL,
            IrrigationSource.MIXED,
        }:
            conflicts.append(
                "Water availability is LOW but an irrigation source is selected. Confirm whether irrigation is assured year-round or only occasional."
            )

        # Soft conflict: High-profit goal with low risk tolerance (not invalid, but creates trade-offs).
        if request.goal == request.goal.__class__.MAXIMIZE_PROFIT and request.risk_tolerance == RiskLevel.LOW:
            conflicts.append(
                "Goal is MAXIMIZE_PROFIT but risk tolerance is LOW. Recommendations will prioritise safer profit options and may reduce expected upside."
            )

        # ── Write state ──────────────────────────────────────────────
        state["validated_profile"] = validated
        state["hard_constraints"] = hard
        state["soft_constraints"] = soft
        state["warnings"] = warnings
        state["conflicts"] = conflicts

        return state
