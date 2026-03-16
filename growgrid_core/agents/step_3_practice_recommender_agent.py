"""Agent 3 — Type of Farming Recommender (Practice Selection).

Uses structured practice intelligence plus downstream crop outlook
signals to select the best farming model for the user's constraints.
Deterministic: hard filters -> expert fit scoring -> weighted sum -> ranking.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.agents.step_2_goal_classifier_agent import SCORING_DIMENSIONS
from growgrid_core.config import PRACTICE_ALTERNATIVES_COUNT
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import (
    get_all_practices,
    get_crop_count_by_practice,
    get_crops_for_practice,
    get_practice_infrastructure,
    get_practice_irrigation_suitability,
    get_practice_location_suitability,
    get_suitability_by_state,
)
from growgrid_core.utils.location import parse_state_from_location
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

_PRACTICE_SUITABILITY_SCORE = {
    "GOOD": 1.0,
    "MED": 0.75,
    "MEDIUM": 0.75,
    "POOR": 0.35,
    "LOW": 0.35,
    "NOT_FEASIBLE": 0.0,
}

_PRACTICE_LOCATION_MULTIPLIER = {
    "GOOD": 1.08,
    "MED": 1.0,
    "MEDIUM": 1.0,
    "POOR": 0.82,
    "LOW": 0.82,
    "NOT_FEASIBLE": 0.0,
}

_EXPOSURE_PENALTY = {"LOW": 0.0, "MED": 0.08, "HIGH": 0.18}
_STORAGE_PENALTY = {"LOW": 0.0, "MED": 0.07, "HIGH": 0.16}


@dataclass
class PracticeAnalysis:
    fit_scores: dict[str, float]
    score_multiplier: float
    elimination_reason: str | None = None
    summary: str = ""


class PracticeRecommenderAgent(BaseAgent):
    """Select top farming practice via hard filters + expert scoring."""

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
        state_name = parse_state_from_location(profile.location)
        suitability_by_crop = get_suitability_by_state(conn, state_name) if state_name else {}

        all_scores: list[PracticeScore] = []
        practice_reason_lookup: dict[str, str] = {}

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

            analysis = self._analyze_practice(
                conn=conn,
                practice_row=p,
                profile=profile,
                weights=w,
                hard_constraints=hard_constraints,
                state_name=state_name,
                suitability_by_crop=suitability_by_crop,
                global_crop_count=n_crops,
            )
            if analysis.elimination_reason:
                all_scores.append(
                    PracticeScore(
                        practice_code=practice_code,
                        practice_name=p.get("practice_name", "Unknown"),
                        fit_scores={},
                        weighted_score=0.0,
                        eliminated=True,
                        elimination_reason=analysis.elimination_reason,
                    )
                )
                continue

            assert set(analysis.fit_scores.keys()) == set(SCORING_DIMENSIONS), (
                "Fit dimensions must match SCORING_DIMENSIONS"
            )

            score = weighted_sum(analysis.fit_scores, w) * analysis.score_multiplier
            score = max(0.0, min(score, 1.5))
            practice_reason_lookup[practice_code] = analysis.summary

            all_scores.append(
                PracticeScore(
                    practice_code=practice_code,
                    practice_name=p.get("practice_name", "Unknown"),
                    fit_scores=analysis.fit_scores,
                    weighted_score=round(score, 4),
                    eliminated=False,
                )
            )

        feasible = [score for score in all_scores if not score.eliminated]
        feasible = self._apply_tiebreaker(feasible, practices)

        if not feasible:
            logger.info(
                "No feasible practice: all %d practices eliminated after expert scoring.",
                len(all_scores),
            )
            state["practice_ranking"] = all_scores
            state["selected_practice"] = PracticeScore(
                practice_code="NONE",
                practice_name="No feasible practice found",
                fit_scores={},
                weighted_score=0.0,
                eliminated=True,
                elimination_reason=(
                    "All practices were eliminated by hard filters or lacked a viable crop pathway "
                    "for the current location and resources."
                ),
            )
            state["practice_alternatives"] = []
            state["selected_practice_reason"] = "No practice passed expert feasibility checks."
            return state

        n_alt = max(0, min(PRACTICE_ALTERNATIVES_COUNT, len(feasible) - 1))
        selected = feasible[0]
        state["practice_ranking"] = all_scores
        state["selected_practice"] = selected
        state["practice_alternatives"] = feasible[1 : 1 + n_alt]

        reason = practice_reason_lookup.get(selected.practice_code, "")
        if reason:
            state["selected_practice_reason"] = (
                f"{reason} Final weighted score: {selected.weighted_score:.3f}."
            )
        else:
            state["selected_practice_reason"] = (
                f"Highest weighted score ({selected.weighted_score:.3f}) and best fit for your constraints."
            )

        logger.info(
            "Selected practice: %s (score=%.3f), %d alternative(s)",
            selected.practice_code,
            selected.weighted_score,
            n_alt,
        )
        return state

    @staticmethod
    def _check_hard_filters(
        p: dict,
        profile: ValidatedProfile,
        hard_constraints: list[HardConstraint],
    ) -> str | None:
        """Return elimination reason or None if practice passes."""
        for hc in hard_constraints:
            if hc.operator == "exclude_practice_codes" and hc.dimension == "practice":
                excluded = {code.strip().upper() for code in hc.threshold.split(",") if code.strip()}
                if p.get("practice_code", "").upper() in excluded:
                    return hc.reason

            if hc.operator == "exclude_if_equal" and hc.threshold == "HIGH":
                if hc.dimension == "water" and p.get("water_need") == "HIGH":
                    return hc.reason
                if hc.dimension == "labour" and p.get("labour_need") == "HIGH":
                    return hc.reason
                if hc.dimension == "risk" and p.get("risk_level") == "HIGH":
                    return hc.reason

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

    @staticmethod
    def _compute_fits(p: dict, profile: ValidatedProfile) -> dict[str, float]:
        """Compute the base 6-dimension fit scores for a practice."""
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

    def _analyze_practice(
        self,
        *,
        conn: sqlite3.Connection,
        practice_row: dict[str, Any],
        profile: ValidatedProfile,
        weights: dict[str, float],
        hard_constraints: list[HardConstraint],
        state_name: str | None,
        suitability_by_crop: dict[str, dict],
        global_crop_count: int,
    ) -> PracticeAnalysis:
        practice_code = practice_row.get("practice_code", "UNKNOWN")
        base_fits = self._compute_fits(practice_row, profile)

        irrigation_row = get_practice_irrigation_suitability(
            conn,
            practice_code,
            profile.irrigation_source.value,
        )
        irrigation_label = (irrigation_row or {}).get("suitability", "MED")
        irrigation_fit = _PRACTICE_SUITABILITY_SCORE.get(irrigation_label, 0.75)
        if irrigation_fit <= 0:
            return PracticeAnalysis(
                fit_scores={},
                score_multiplier=0.0,
                elimination_reason=(irrigation_row or {}).get(
                    "rationale",
                    f"{practice_code} is not feasible with {profile.irrigation_source.value} irrigation.",
                ),
            )

        location_row = get_practice_location_suitability(conn, practice_code, state_name)
        location_label = (location_row or {}).get("suitability", "MED")
        location_multiplier = _PRACTICE_LOCATION_MULTIPLIER.get(location_label, 1.0)
        if location_multiplier <= 0:
            return PracticeAnalysis(
                fit_scores={},
                score_multiplier=0.0,
                elimination_reason=(location_row or {}).get(
                    "rationale",
                    f"{practice_code} is not recommended for {state_name or 'this location'}.",
                ),
            )

        infra_rows = get_practice_infrastructure(conn, practice_code)
        required_count = sum(
            1 for row in infra_rows if (row.get("requirement_level") or "").upper() == "REQUIRED"
        )
        recommended_count = sum(
            1 for row in infra_rows if (row.get("requirement_level") or "").upper() == "RECOMMENDED"
        )
        management_load = min(1.0, (required_count + 0.5 * recommended_count) / 8.0)

        crop_outlook = self._practice_crop_outlook(
            conn=conn,
            practice_code=practice_code,
            profile=profile,
            weights=weights,
            hard_constraints=hard_constraints,
            suitability_by_crop=suitability_by_crop,
        )
        if crop_outlook["feasible_crop_count"] == 0:
            return PracticeAnalysis(
                fit_scores={},
                score_multiplier=0.0,
                elimination_reason=(
                    "No crops under this practice appear viable for the current horizon, "
                    "risk, water, and location constraints."
                ),
            )

        opex_min = float(practice_row.get("opex_min_per_acre_inr") or 0)
        opex_max = float(practice_row.get("opex_max_per_acre_inr") or max(opex_min, 1))
        capex_min = float(practice_row.get("capex_min_per_acre_inr") or 0)
        capex_max = float(practice_row.get("capex_max_per_acre_inr") or max(capex_min, 1))
        first_year_min = capex_min + opex_min
        first_year_max = capex_max + opex_max
        first_year_fit = capex_fit(profile.budget_per_acre, first_year_min, first_year_max)

        perishability = (practice_row.get("perishability_exposure") or "MED").upper()
        storage_dependency = (practice_row.get("storage_dependency") or "MED").upper()
        perish_penalty = _EXPOSURE_PENALTY.get(perishability, 0.08)
        storage_penalty = _STORAGE_PENALTY.get(storage_dependency, 0.07)
        stability_score = _clamp(1.0 - perish_penalty - storage_penalty - (0.10 * management_load))
        goal_alignment_multiplier = _goal_alignment_multiplier(practice_row, profile, stability_score)

        labour_penalty = 0.0
        if profile.labour_availability.value == "LOW":
            labour_penalty = 0.18 * management_load
        elif profile.labour_availability.value == "MED":
            labour_penalty = 0.08 * management_load

        adjusted_fits = {
            "water": round(_clamp((0.70 * base_fits["water"]) + (0.30 * irrigation_fit)), 4),
            "labour": round(_clamp(base_fits["labour"] - labour_penalty), 4),
            "capex": round(_clamp((0.65 * base_fits["capex"]) + (0.35 * first_year_fit)), 4),
            "time": round(
                _clamp((0.65 * base_fits["time"]) + (0.35 * crop_outlook["avg_time_fit"])),
                4,
            ),
            "risk": round(
                _clamp(
                    (0.60 * base_fits["risk"])
                    + (0.25 * crop_outlook["avg_risk_fit"])
                    + (0.15 * stability_score)
                ),
                4,
            ),
            "profit": round(
                _clamp((0.70 * base_fits["profit"]) + (0.30 * crop_outlook["avg_profit_fit"])),
                4,
            ),
        }

        score_multiplier = location_multiplier
        score_multiplier *= crop_outlook["outlook_multiplier"]
        score_multiplier *= crop_outlook["diversity_multiplier"]
        score_multiplier *= goal_alignment_multiplier
        if global_crop_count <= 3:
            score_multiplier *= 0.96
        elif global_crop_count <= 6:
            score_multiplier *= 0.99

        summary_bits: list[str] = []
        if state_name and location_label == "GOOD":
            summary_bits.append(f"strong fit for {state_name}")
        if irrigation_label == "GOOD":
            summary_bits.append(
                f"good match for {profile.irrigation_source.value.lower()} irrigation"
            )
        elif irrigation_label == "POOR":
            summary_bits.append("irrigation setup is less ideal")
        if adjusted_fits["capex"] >= 0.85:
            summary_bits.append("budget fit is strong")
        elif adjusted_fits["capex"] < 0.55:
            summary_bits.append("working-capital fit is tight")
        if crop_outlook["best_crop_names"]:
            summary_bits.append(
                "top crop pathways look strong: " + ", ".join(crop_outlook["best_crop_names"][:2])
            )
        if goal_alignment_multiplier > 1.04:
            summary_bits.append("strong alignment with your primary goal")
        summary = "; ".join(summary_bits) if summary_bits else "Best overall expert fit across resources and crop outlook."

        return PracticeAnalysis(
            fit_scores=adjusted_fits,
            score_multiplier=round(score_multiplier, 4),
            summary=summary,
        )

    def _practice_crop_outlook(
        self,
        *,
        conn: sqlite3.Connection,
        practice_code: str,
        profile: ValidatedProfile,
        weights: dict[str, float],
        hard_constraints: list[HardConstraint],
        suitability_by_crop: dict[str, dict],
    ) -> dict[str, Any]:
        candidates = get_crops_for_practice(conn, practice_code)
        feasible_rows: list[dict[str, Any]] = []

        for crop in candidates:
            if self._crop_conflicts_with_profile(crop, profile, hard_constraints):
                continue

            loc_mult = _crop_location_suitability_multiplier(crop["crop_id"], suitability_by_crop)
            season_mult = _season_multiplier(profile.planning_month, crop.get("seasons_supported"))
            fits = {
                "water": ordinal_fit(profile.water_availability.value, crop.get("water_need", "MED")),
                "labour": ordinal_fit(profile.labour_availability.value, crop.get("labour_need", "MED")),
                "time": time_fit(
                    profile.horizon_months,
                    crop.get("time_to_first_income_months_min", 0),
                    crop.get("time_to_first_income_months_max", crop.get("time_to_first_income_months_min", 0)),
                ),
                "risk": risk_fit(profile.risk_tolerance.value, crop.get("risk_level", "MED")),
                "profit": profit_fit(crop.get("profit_potential", "MED")),
            }
            score = _weighted_sum_partial(fits, weights)
            score *= float(crop.get("compatibility_score", 0) or 0)
            score *= loc_mult
            score *= season_mult
            feasible_rows.append(
                {
                    "crop_id": crop["crop_id"],
                    "crop_name": crop["crop_name"],
                    "category": crop.get("category", ""),
                    "score": score,
                    "fits": fits,
                }
            )

        feasible_rows.sort(key=lambda row: (-row["score"], row["crop_id"]))
        if not feasible_rows:
            return {
                "feasible_crop_count": 0,
                "avg_score": 0.0,
                "avg_profit_fit": 0.0,
                "avg_time_fit": 0.0,
                "avg_risk_fit": 0.0,
                "outlook_multiplier": 0.0,
                "diversity_multiplier": 0.0,
                "best_crop_names": [],
            }

        top_rows = feasible_rows[: min(3, len(feasible_rows))]
        avg_score = sum(row["score"] for row in top_rows) / len(top_rows)
        avg_profit_fit = sum(row["fits"]["profit"] for row in top_rows) / len(top_rows)
        avg_time_fit = sum(row["fits"]["time"] for row in top_rows) / len(top_rows)
        avg_risk_fit = sum(row["fits"]["risk"] for row in top_rows) / len(top_rows)
        category_count = len({row["category"] for row in feasible_rows[:5] if row["category"]})
        feasible_crop_count = len(feasible_rows)

        if feasible_crop_count <= 2:
            diversity_multiplier = 0.96
        elif feasible_crop_count <= 5:
            diversity_multiplier = 1.0
        elif feasible_crop_count <= 10:
            diversity_multiplier = 1.03
        else:
            diversity_multiplier = 1.05
        if category_count >= 2:
            diversity_multiplier += 0.01

        outlook_multiplier = _clamp(0.90 + min(avg_score, 1.0) * 0.18, low=0.90, high=1.12)

        return {
            "feasible_crop_count": feasible_crop_count,
            "avg_score": avg_score,
            "avg_profit_fit": avg_profit_fit,
            "avg_time_fit": avg_time_fit,
            "avg_risk_fit": avg_risk_fit,
            "outlook_multiplier": round(outlook_multiplier, 4),
            "diversity_multiplier": round(_clamp(diversity_multiplier, low=0.95, high=1.08), 4),
            "best_crop_names": [row["crop_name"] for row in top_rows],
        }

    @staticmethod
    def _crop_conflicts_with_profile(
        crop_row: dict[str, Any],
        profile: ValidatedProfile,
        hard_constraints: list[HardConstraint],
    ) -> bool:
        for hc in hard_constraints:
            if hc.operator != "exclude_if_equal":
                continue
            if hc.dimension == "water" and hc.threshold == "HIGH" and crop_row.get("water_need") == "HIGH":
                return True
            if hc.dimension == "labour" and hc.threshold == "HIGH" and crop_row.get("labour_need") == "HIGH":
                return True
            if hc.dimension == "risk" and hc.threshold == "HIGH" and crop_row.get("risk_level") == "HIGH":
                return True

        if profile.horizon_months < (crop_row.get("time_to_first_income_months_min") or 0):
            return True
        if profile.risk_tolerance.value == "LOW" and crop_row.get("risk_level") == "HIGH":
            return True
        return False

    @staticmethod
    def _apply_tiebreaker(
        feasible: list[PracticeScore],
        raw_practices: list[dict],
    ) -> list[PracticeScore]:
        """Sort by weighted score (desc), then by lower risk (LOW < MED < HIGH)."""
        if not feasible:
            return feasible
        risk_order = {"LOW": 0, "MED": 1, "HIGH": 2}
        lookup = {p.get("practice_code", ""): p for p in raw_practices}

        def sort_key(score: PracticeScore) -> tuple:
            row = lookup.get(score.practice_code, {})
            risk_rank = risk_order.get(row.get("risk_level", "HIGH"), 2)
            return (-score.weighted_score, risk_rank, score.practice_code)

        return sorted(feasible, key=sort_key)


def _weighted_sum_partial(fits: dict[str, float], weights: dict[str, float]) -> float:
    used_dims = [dim for dim in fits if dim in weights]
    if not used_dims:
        return 0.0
    used_weight_mass = sum(weights[dim] for dim in used_dims)
    if used_weight_mass <= 0:
        return 0.0
    raw = sum(weights[dim] * fits[dim] for dim in used_dims)
    return raw / used_weight_mass


def _crop_location_suitability_multiplier(crop_id: str, suitability_by_crop: dict[str, dict]) -> float:
    row = suitability_by_crop.get(crop_id)
    if not row:
        return 0.85
    suit = (row.get("suitability") or "").strip().upper()
    return {"GOOD": 1.0, "MED": 0.75, "MEDIUM": 0.75, "LOW": 0.5}.get(suit, 0.85)


def _season_multiplier(planning_month: int | None, seasons_supported: str | None) -> float:
    if not planning_month or not seasons_supported or not (seasons_supported or "").strip():
        return 1.0
    supported = {season.strip().upper() for season in (seasons_supported or "").split(",") if season.strip()}
    if not supported:
        return 1.0
    current = "KHARIF" if planning_month in (6, 7, 8, 9, 10) else "RABI"
    if current in supported or "BOTH" in supported or "ALL" in supported:
        return 1.0
    if "ZAID" in supported and planning_month in (3, 4, 5):
        return 1.0
    return 0.55


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _goal_alignment_multiplier(
    practice_row: dict[str, Any],
    profile: ValidatedProfile,
    stability_score: float,
) -> float:
    """Goal-specific expert multiplier to let specialist practices surface when appropriate."""
    goal = profile.goal.value
    profit_potential = (practice_row.get("profit_potential") or "MED").upper()
    risk_level = (practice_row.get("risk_level") or "MED").upper()
    water_need = (practice_row.get("water_need") or "MED").upper()
    time_min = int(practice_row.get("time_to_first_income_months_min") or 0)

    multiplier = 1.0

    if goal == "MAXIMIZE_PROFIT":
        multiplier *= {"LOW": 0.94, "MED": 0.98, "HIGH": 1.04, "VERY_HIGH": 1.10}.get(
            profit_potential,
            1.0,
        )
    elif goal == "FAST_ROI":
        if time_min <= 2:
            multiplier *= 1.10
        elif time_min <= 4:
            multiplier *= 1.05
        elif time_min <= 6:
            multiplier *= 1.0
        else:
            multiplier *= 0.92
    elif goal == "WATER_SAVING":
        multiplier *= {"LOW": 1.10, "MED": 1.0, "HIGH": 0.88}.get(water_need, 1.0)
    elif goal == "STABLE_INCOME":
        multiplier *= {"LOW": 1.08, "MED": 1.0, "HIGH": 0.90}.get(risk_level, 1.0)
        if stability_score >= 0.80:
            multiplier *= 1.03

    return _clamp(multiplier, low=0.88, high=1.15)
