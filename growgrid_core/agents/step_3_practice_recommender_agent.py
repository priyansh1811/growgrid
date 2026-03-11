"""Agent 3 — Type of Farming Recommender (Practice Selection).

Uses PracticeDB + goal weights to select the best farming model.
Deterministic: hard filters → fit scoring → weighted sum → ranking.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.agents.step_2_goal_classifier_agent import SCORING_DIMENSIONS
from growgrid_core.config import PRACTICE_ALTERNATIVES_COUNT
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import get_all_practices, get_crop_count_by_practice
from growgrid_core.utils.scoring import (
    capex_fit,
    ordinal_fit,
    profit_fit,
    risk_fit,
    time_fit,
    weighted_sum,
)
from growgrid_core.utils.types import (
    HardConstraint,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
    WeightVector,
)

logger = logging.getLogger(__name__)


class PracticeRecommenderAgent(BaseAgent):
    """Select top farming practice via hard filters + weighted scoring."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return load_all()

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]
        weights: WeightVector = state["goal_weights"]
        w = weights.as_dict()

        conn = self._get_conn()
        practices = get_all_practices(conn)
        hard_constraints: list[HardConstraint] = state.get("hard_constraints", [])
        crop_counts = get_crop_count_by_practice(conn)

        all_scores: list[PracticeScore] = []

        for p in practices:
            practice_code = p.get("practice_code", "UNKNOWN")

            elimination_reason = self._check_hard_filters(p, profile, hard_constraints)

            if elimination_reason:
                all_scores.append(
                    PracticeScore(
                        practice_code=practice_code,
                        practice_name=p.get("practice_name", "Unknown"),
                        fit_scores={},
                        weighted_score=0.0,
                        eliminated=True,
                        elimination_reason=elimination_reason,
                    )
                )
                continue

            # Eliminate practices with no compatible crops in the database
            n_crops = crop_counts.get(practice_code, 0)
            if n_crops == 0:
                all_scores.append(
                    PracticeScore(
                        practice_code=practice_code,
                        practice_name=p.get("practice_name", "Unknown"),
                        fit_scores={},
                        weighted_score=0.0,
                        eliminated=True,
                        elimination_reason="No compatible crops defined for this practice.",
                    )
                )
                continue

            fits = self._compute_fits(p, profile)
            assert set(fits.keys()) == set(SCORING_DIMENSIONS), "Fit dimensions must match SCORING_DIMENSIONS"
            score = weighted_sum(fits, w)

            # Soft diversity penalty: favor practices with broader crop pools
            if n_crops <= 2:
                score *= 0.90
            elif n_crops <= 5:
                score *= 0.95

            all_scores.append(
                PracticeScore(
                    practice_code=practice_code,
                    practice_name=p.get("practice_name", "Unknown"),
                    fit_scores=fits,
                    weighted_score=round(score, 4),
                    eliminated=False,
                )
            )

        # Rank surviving practices; tiebreaker by lower risk for full list
        feasible = [s for s in all_scores if not s.eliminated]
        feasible = self._apply_tiebreaker(feasible, practices)

        if not feasible:
            logger.info(
                "No feasible practice: all %d practices eliminated by hard constraints",
                len(all_scores),
            )
            state["practice_ranking"] = all_scores
            state["selected_practice"] = PracticeScore(
                practice_code="NONE",
                practice_name="No feasible practice found",
                fit_scores={},
                weighted_score=0.0,
                eliminated=True,
                elimination_reason="All practices eliminated by hard constraints. "
                "Consider relaxing budget, water, or labour constraints.",
            )
            state["practice_alternatives"] = []
            state["selected_practice_reason"] = "No practice passed hard filters."
            return state

        n_alt = max(0, min(PRACTICE_ALTERNATIVES_COUNT, len(feasible) - 1))
        state["practice_ranking"] = all_scores
        state["selected_practice"] = feasible[0]
        state["practice_alternatives"] = feasible[1 : 1 + n_alt]
        state["selected_practice_reason"] = (
            f"Highest weighted score ({feasible[0].weighted_score:.3f}); "
            + ("lower risk than ties." if len(feasible) > 1 and feasible[1].weighted_score == feasible[0].weighted_score else "best fit for your constraints.")
        )
        logger.info(
            "Selected practice: %s (score=%.3f), %d alternative(s)",
            feasible[0].practice_code,
            feasible[0].weighted_score,
            n_alt,
        )
        return state

    # ── Hard filters ─────────────────────────────────────────────────

    @staticmethod
    def _check_hard_filters(
        p: dict,
        profile: ValidatedProfile,
        hard_constraints: list[HardConstraint],
    ) -> str | None:
        """Return elimination reason or None if practice passes."""
        # Apply constraint-driven eliminations first (emitted by ValidationAgent)
        for hc in hard_constraints:
            if hc.operator == "exclude_practice_codes" and hc.dimension == "practice":
                excluded = {c.strip().upper() for c in hc.threshold.split(",") if c.strip()}
                if p.get("practice_code", "").upper() in excluded:
                    return hc.reason

            # Generic HIGH bans (water/labour/risk) are enforced here as well
            if hc.operator == "exclude_if_equal" and hc.threshold == "HIGH":
                if hc.dimension == "water" and p.get("water_need") == "HIGH":
                    return hc.reason
                if hc.dimension == "labour" and p.get("labour_need") == "HIGH":
                    return hc.reason
                if hc.dimension == "risk" and p.get("risk_level") == "HIGH":
                    return hc.reason

        # Redundant with hard_constraints but kept for robustness if constraints change
        water_need = p.get("water_need", "")
        if profile.water_availability == profile.water_availability.__class__.LOW and water_need == "HIGH":
            return "Water availability LOW; practice requires HIGH water."

        labour_need = p.get("labour_need", "")
        if profile.labour_availability == profile.labour_availability.__class__.LOW and labour_need == "HIGH":
            return "Labour availability LOW; practice requires HIGH labour."

        capex_min = p.get("capex_min_per_acre_inr")
        if capex_min is not None and capex_min > profile.budget_per_acre:
            return (
                f"Budget per acre ({profile.budget_per_acre:.0f}) below "
                f"minimum CAPEX ({capex_min})."
            )

        time_min = p.get("time_to_first_income_months_min")
        if time_min is not None and profile.horizon_months < time_min:
            return (
                f"Horizon ({profile.horizon_months} months) shorter than "
                f"minimum time to income ({time_min} months)."
            )

        risk_level = p.get("risk_level", "")
        if profile.risk_tolerance == profile.risk_tolerance.__class__.LOW and risk_level == "HIGH":
            return "Risk tolerance LOW; practice is HIGH risk."

        return None

    # ── Fit scoring ──────────────────────────────────────────────────

    @staticmethod
    def _compute_fits(p: dict, profile: ValidatedProfile) -> dict[str, float]:
        """Compute 6-dimension fit scores for a practice. Keys must match SCORING_DIMENSIONS."""
        capex_min = p.get("capex_min_per_acre_inr") or 0
        capex_max = p.get("capex_max_per_acre_inr") or max(capex_min, 1)
        time_min = p.get("time_to_first_income_months_min") or 0
        time_max = p.get("time_to_first_income_months_max") or max(time_min, 1)
        return {
            "water": ordinal_fit(profile.water_availability.value, p.get("water_need", "MED")),
            "labour": ordinal_fit(profile.labour_availability.value, p.get("labour_need", "MED")),
            "capex": capex_fit(profile.budget_per_acre, capex_min, capex_max),
            "time": time_fit(profile.horizon_months, time_min, time_max),
            "risk": risk_fit(profile.risk_tolerance.value, p.get("risk_level", "MED")),
            "profit": profit_fit(p.get("profit_potential", "MED")),
        }

    # ── Tiebreaker ───────────────────────────────────────────────────

    @staticmethod
    def _apply_tiebreaker(
        feasible: list[PracticeScore],
        raw_practices: list[dict],
    ) -> list[PracticeScore]:
        """Sort by weighted score (desc), then by lower risk (LOW < MED < HIGH) for full list."""
        if not feasible:
            return feasible
        risk_order = {"LOW": 0, "MED": 1, "HIGH": 2}
        lookup = {p.get("practice_code", ""): p for p in raw_practices}

        def sort_key(s: PracticeScore) -> tuple:
            row = lookup.get(s.practice_code, {})
            risk_rank = risk_order.get(row.get("risk_level", "HIGH"), 2)
            return (-s.weighted_score, risk_rank, s.practice_code)

        feasible = sorted(feasible, key=sort_key)
        return feasible
