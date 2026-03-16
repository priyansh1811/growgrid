"""Agent 2 — Goal Classifier (AHP-based + constraint tightening).

Converts the user's goal + resource constraints into a normalised
weight vector W across 6 scoring dimensions.  Purely deterministic.
Practice and crop agents expect weights for these same dimensions.
"""

from __future__ import annotations

from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.config import (
    ALPHA,
    EXTREMELY_LOW_BUDGET_THRESHOLD,
    GOAL_TIME_TIGHTNESS_MONTHS_TIER1,
    GOAL_TIME_TIGHTNESS_MONTHS_TIER2,
    GOAL_TIME_TIGHTNESS_MONTHS_TIER3,
    GOAL_WEIGHT_MAX_MULTIPLIER,
    LOW_BUDGET_WARNING_THRESHOLD,
    POLYHOUSE_MIN_BUDGET_PER_ACRE,
)
from growgrid_core.utils.enums import Goal, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.scoring import normalize_weights
from growgrid_core.utils.types import PlanRequest, ValidatedProfile, WeightVector

# Canonical order of scoring dimensions (must match practice/crop fit score keys)
SCORING_DIMENSIONS: tuple[str, ...] = ("profit", "risk", "water", "labour", "time", "capex")

# ── AHP base-weight templates (offline-derived) ─────────────────────────

_BASE_TEMPLATES: dict[Goal, dict[str, float]] = {
    Goal.MAXIMIZE_PROFIT: {
        "profit": 0.431, "risk": 0.151, "water": 0.139,
        "labour": 0.097, "time": 0.092, "capex": 0.092,
    },
    Goal.STABLE_INCOME: {
        "profit": 0.085, "risk": 0.418, "water": 0.184,
        "labour": 0.098, "time": 0.112, "capex": 0.103,
    },
    Goal.WATER_SAVING: {
        "profit": 0.058, "risk": 0.190, "water": 0.426,
        "labour": 0.090, "time": 0.094, "capex": 0.142,
    },
    Goal.FAST_ROI: {
        "profit": 0.225, "risk": 0.086, "water": 0.086,
        "labour": 0.053, "time": 0.403, "capex": 0.146,
    },
}

# ── Tightness helpers ────────────────────────────────────────────────────

_OrdinalTightnessKey = WaterLevel | LabourLevel | RiskLevel
_ORDINAL_TIGHTNESS: dict[_OrdinalTightnessKey, float] = {
    WaterLevel.LOW: 1.0,
    WaterLevel.MED: 0.5,
    WaterLevel.HIGH: 0.0,
    LabourLevel.LOW: 1.0,
    LabourLevel.MED: 0.5,
    LabourLevel.HIGH: 0.0,
    RiskLevel.LOW: 1.0,
    RiskLevel.MED: 0.5,
    RiskLevel.HIGH: 0.0,
}


def _time_tightness(horizon_months: int) -> float:
    if horizon_months <= GOAL_TIME_TIGHTNESS_MONTHS_TIER1:
        return 1.0
    if horizon_months <= GOAL_TIME_TIGHTNESS_MONTHS_TIER2:
        return 0.7
    if horizon_months <= GOAL_TIME_TIGHTNESS_MONTHS_TIER3:
        return 0.4
    return 0.1


def _capex_tightness(budget_per_acre: float) -> float:
    """Use same budget tiers as validation agent for consistency."""
    if budget_per_acre < EXTREMELY_LOW_BUDGET_THRESHOLD:
        return 1.0
    if budget_per_acre < LOW_BUDGET_WARNING_THRESHOLD:
        return 0.7
    if budget_per_acre < POLYHOUSE_MIN_BUDGET_PER_ACRE:
        return 0.4
    return 0.1


# ── Agent ────────────────────────────────────────────────────────────────


class GoalClassifierAgent(BaseAgent):
    """Compute AHP weight vector W, adjusted by resource tightness."""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]

        # 1. Base template (fallback to equal weights if goal has no template)
        if profile.goal in _BASE_TEMPLATES:
            base = dict(_BASE_TEMPLATES[profile.goal])
            used_fallback = False
        else:
            base = {dim: 1.0 / len(SCORING_DIMENSIONS) for dim in SCORING_DIMENSIONS}
            used_fallback = True

        # 2. Compute tightness per dimension
        tightness: dict[str, float] = {
            "profit": 0.0,  # always 0
            "risk": _ORDINAL_TIGHTNESS[profile.risk_tolerance],
            "water": _ORDINAL_TIGHTNESS[profile.water_availability],
            "labour": _ORDINAL_TIGHTNESS[profile.labour_availability],
            "time": _time_tightness(profile.horizon_months),
            "capex": _capex_tightness(profile.budget_per_acre),
        }

        # 3. Adjust with cap so one dimension doesn't dominate
        adjusted = {}
        for dim in base:
            mult = 1.0 + ALPHA * tightness[dim]
            mult = min(mult, GOAL_WEIGHT_MAX_MULTIPLIER)
            adjusted[dim] = base[dim] * mult

        # 4. Normalize
        final = normalize_weights(adjusted)

        # 5. Build explanation
        explanation_parts: list[str] = [
            f"Base weights from AHP template for goal '{profile.goal.value}'."
            if not used_fallback
            else f"No template for goal '{profile.goal.value}'; used equal weights.",
            f"Constraint tightening applied with alpha={ALPHA:.2f} (max multiplier={GOAL_WEIGHT_MAX_MULTIPLIER}) and then normalized.",
        ]

        for dim in sorted(tightness.keys()):
            t = tightness[dim]
            if t > 0:
                explanation_parts.append(
                    f"  {dim}: tightness={t:.1f} | base={base[dim]:.3f} → adjusted={adjusted[dim]:.3f} → final={final[dim]:.3f}"
                )

        state["goal_weights"] = WeightVector(**final)
        state["goal_tightness"] = tightness
        state["goal_explanation"] = "\n".join(explanation_parts)

        return state
