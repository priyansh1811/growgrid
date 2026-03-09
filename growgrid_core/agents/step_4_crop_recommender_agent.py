"""Agent 4 — Crop Recommender (Crop Portfolio).

Given the selected practice, recommend 1-3 crops with area split.
Core is deterministic: compatibility filter → hard filters → scoring → portfolio.
Optional LLM layer: user-context → soft preferences; portfolio → explanation.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.config import (
    CROP_LLM_LAYER_ENABLED,
    DIVERSIFY_LAND_THRESHOLD_2,
    DIVERSIFY_LAND_THRESHOLD_3,
    OPENAI_API_KEY,
)
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import get_crops_for_practice, get_suitability_by_state
from growgrid_core.tools.llm_client import BaseLLMClient, get_llm_client
from growgrid_core.utils.scoring import (
    ordinal_fit,
    profit_fit,
    risk_fit,
    time_fit,
)
from growgrid_core.utils.types import (
    CropPortfolioEntry,
    CropScore,
    HardConstraint,
    PlanRequest,
    PracticeScore,
    SoftConstraint,
    ValidatedProfile,
    WeightVector,
)

logger = logging.getLogger(__name__)


class CropRecommenderAgent(BaseAgent):
    """Recommend crop portfolio for the selected practice.

    Optional LLM layer (when CROP_LLM_LAYER_ENABLED and client available):
    - Derive soft preferences from user_context and merge into scoring.
    - Generate selected_crop_portfolio_reason after building portfolio.
    """

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self._conn = conn
        self._llm_client = llm_client

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return load_all()

    def _get_llm(self) -> BaseLLMClient | None:
        if self._llm_client is not None:
            return self._llm_client
        if not (OPENAI_API_KEY or "").strip():
            return None
        return get_llm_client()

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]
        weights: WeightVector = state["goal_weights"]
        selected_practice: PracticeScore = state["selected_practice"]
        hard_constraints: list[HardConstraint] = state.get("hard_constraints", [])
        soft_constraints: list[SoftConstraint] = list(state.get("soft_constraints", []))
        user_context: str | None = getattr(profile, "user_context", None) or getattr(
            request, "user_context", None
        )
        w = weights.as_dict()

        if selected_practice.eliminated:
            state["crop_ranking"] = []
            state["selected_crop_portfolio"] = []
            state["selected_crop_portfolio_reason"] = "No practice selected; no crop portfolio."
            return state

        # Optional LLM: derive soft preferences from user_context
        llm = self._get_llm()
        if llm and CROP_LLM_LAYER_ENABLED and user_context and (user_context or "").strip():
            extra_soft = _llm_soft_preferences(llm, (user_context or "").strip(), profile)
            soft_constraints = soft_constraints + extra_soft

        conn = self._get_conn()
        candidates = get_crops_for_practice(conn, selected_practice.practice_code)

        # Location-based suitability: state parsed from profile.location, score/eliminate by state data
        state_name = _state_from_location(profile.location)
        suitability_by_crop = get_suitability_by_state(conn, state_name) if state_name else {}

        # Lookups for portfolio selection/explanations
        category_by_id: dict[str, str] = {c["crop_id"]: c.get("category", "") for c in candidates}
        role_by_id: dict[str, str] = {c["crop_id"]: c.get("role_hint", "PRIMARY") for c in candidates}

        all_scores: list[CropScore] = []

        for c in candidates:
            elimination_reason = self._check_hard_filters(c, profile, hard_constraints)

            if elimination_reason:
                all_scores.append(
                    CropScore(
                        crop_id=c["crop_id"],
                        crop_name=c["crop_name"],
                        fit_scores={},
                        compatibility_score=c["compatibility_score"],
                        final_score=0.0,
                        eliminated=True,
                        elimination_reason=elimination_reason,
                    )
                )
                continue

            # Location suitability: eliminate if NOT_SUITABLE; otherwise apply multiplier
            loc_elimination = _location_elimination(c["crop_id"], suitability_by_crop)
            if loc_elimination:
                all_scores.append(
                    CropScore(
                        crop_id=c["crop_id"],
                        crop_name=c["crop_name"],
                        fit_scores={},
                        compatibility_score=c["compatibility_score"],
                        final_score=0.0,
                        eliminated=True,
                        elimination_reason=loc_elimination,
                    )
                )
                continue

            fits = self._compute_fits(c, profile)

            # Partial weighted sum: WeightVector has 6 dims, but crop fit currently uses 5 (capex omitted).
            # We compute score using only the intersection and renormalize by used-weight mass.
            base_score = _weighted_sum_partial(fits, w)

            # Apply soft penalties (e.g., water=MED penalise HIGH-water crops)
            base_score = _apply_soft_penalties(base_score, c, soft_constraints)

            compat = c["compatibility_score"]
            location_mult = _location_suitability_multiplier(c["crop_id"], suitability_by_crop)
            season_mult = _season_multiplier(profile.planning_month, c.get("seasons_supported"))
            final = round(base_score * compat * location_mult * season_mult, 4)

            all_scores.append(
                CropScore(
                    crop_id=c["crop_id"],
                    crop_name=c["crop_name"],
                    fit_scores=fits,
                    compatibility_score=compat,
                    final_score=final,
                    eliminated=False,
                )
            )

        # Rank
        feasible = [s for s in all_scores if not s.eliminated]
        feasible.sort(key=lambda s: (-s.final_score, s.crop_id))

        # Build portfolio
        portfolio = self._build_portfolio(feasible, profile, category_by_id, role_by_id)

        state["crop_ranking"] = all_scores
        state["selected_crop_portfolio"] = portfolio

        # Optional LLM: human-readable explanation; else deterministic fallback
        if not portfolio:
            state["selected_crop_portfolio_reason"] = "No feasible crops for this practice and constraints."
        elif llm and CROP_LLM_LAYER_ENABLED:
            state["selected_crop_portfolio_reason"] = _llm_portfolio_explanation(
                llm, profile, weights, selected_practice, portfolio, user_context
            )
        else:
            state["selected_crop_portfolio_reason"] = _deterministic_portfolio_reason(
                portfolio, profile
            )
        return state

    # ── Hard filters ─────────────────────────────────────────────────

    @staticmethod
    def _check_hard_filters(
        c: dict,
        profile: ValidatedProfile,
        hard_constraints: list[HardConstraint],
    ) -> str | None:
        """Return elimination reason or None.

        Enforces:
        - explicit checks (horizon)
        - state-driven hard constraints (water/labour/risk exclude_if_equal HIGH)
        """
        # State-driven gates (from ValidationAgent)
        for hc in hard_constraints:
            if hc.operator != "exclude_if_equal":
                continue
            if hc.dimension == "water" and hc.threshold == "HIGH" and c.get("water_need") == "HIGH":
                return hc.reason
            if hc.dimension == "labour" and hc.threshold == "HIGH" and c.get("labour_need") == "HIGH":
                return hc.reason
            if hc.dimension == "risk" and hc.threshold == "HIGH" and c.get("risk_level") == "HIGH":
                return hc.reason

        # Explicit horizon gate (crop-specific)
        if profile.horizon_months < c["time_to_first_income_months_min"]:
            return (
                f"Horizon ({profile.horizon_months}mo) shorter than "
                f"crop min income time ({c['time_to_first_income_months_min']}mo)."
            )

        # Keep a conservative direct risk gate (even if hard constraints absent)
        if profile.risk_tolerance.value == "LOW" and c["risk_level"] == "HIGH":
            return "Risk tolerance LOW; crop is HIGH risk."

        return None

    # ── Fit scoring ──────────────────────────────────────────────────

    @staticmethod
    def _compute_fits(c: dict, profile: ValidatedProfile) -> dict[str, float]:
        """5-dimension fit scoring (capex omitted until crop_cost_profile exists)."""
        return {
            "water": ordinal_fit(profile.water_availability.value, c["water_need"]),
            "labour": ordinal_fit(profile.labour_availability.value, c["labour_need"]),
            "time": time_fit(
                profile.horizon_months,
                c["time_to_first_income_months_min"],
                c["time_to_first_income_months_max"],
            ),
            "risk": risk_fit(profile.risk_tolerance.value, c["risk_level"]),
            "profit": profit_fit(c["profit_potential"]),
        }

    # ── Portfolio builder ────────────────────────────────────────────

    @staticmethod
    def _build_portfolio(
        feasible: list[CropScore],
        profile: ValidatedProfile,
        category_by_id: dict[str, str],
        role_by_id: dict[str, str],
    ) -> list[CropPortfolioEntry]:
        if not feasible:
            return []

        # Determine how many crops to select
        want_diversity = (
            profile.land_area_acres >= DIVERSIFY_LAND_THRESHOLD_2
            or profile.risk_tolerance.value == "LOW"
        )
        want_three = (
            profile.land_area_acres >= DIVERSIFY_LAND_THRESHOLD_3
            and profile.risk_tolerance.value == "LOW"
        )

        if want_three and len(feasible) >= 3:
            n_crops = 3
        elif want_diversity and len(feasible) >= 2:
            n_crops = 2
        else:
            n_crops = 1

        # Prefer category diversity in top-N (soft tiebreaker)
        selected = _select_diverse(feasible, n_crops, category_by_id)

        # Area split: continuous from relative scores (no hardcoded 70/30 or 50/30/20)
        fractions = _area_fractions_from_scores(selected)

        portfolio: list[CropPortfolioEntry] = []
        for crop, frac in zip(selected, fractions):
            portfolio.append(
                CropPortfolioEntry(
                    crop_id=crop.crop_id,
                    crop_name=crop.crop_name,
                    area_fraction=frac,
                    role_hint=role_by_id.get(crop.crop_id, "PRIMARY"),
                    score=crop.final_score,
                )
            )

        return portfolio


def _state_from_location(location: str) -> str | None:
    """Parse state from location string. E.g. 'Jaipur, Rajasthan' -> 'Rajasthan'; 'Kerala' -> 'Kerala'."""
    if not location or not location.strip():
        return None
    parts = [p.strip() for p in location.strip().split(",") if p.strip()]
    if not parts:
        return None
    return parts[-1] if parts else None


def _location_elimination(crop_id: str, suitability_by_crop: dict[str, dict]) -> str | None:
    """If state has explicit NOT_SUITABLE for this crop, return elimination reason; else None."""
    row = suitability_by_crop.get(crop_id)
    if not row:
        return None
    suit = (row.get("suitability") or "").strip().upper()
    if suit == "NOT_SUITABLE" or suit == "UNSUITABLE":
        rationale = (row.get("rationale") or "Not suitable for this state.")[:120]
        return f"Location suitability: {rationale}"
    return None


def _location_suitability_multiplier(crop_id: str, suitability_by_crop: dict[str, dict]) -> float:
    """Return 0..1 multiplier from state suitability. No data => 0.85 (slight penalty)."""
    row = suitability_by_crop.get(crop_id)
    if not row:
        return 0.85  # no state data: slight penalty
    suit = (row.get("suitability") or "").strip().upper()
    mult = {"GOOD": 1.0, "MED": 0.75, "MEDIUM": 0.75, "LOW": 0.5}.get(suit, 0.85)
    return mult


def _area_fractions_from_scores(selected: list[CropScore]) -> list[float]:
    """Compute area fractions from relative final_score; sum to 1.0. Continuous by score, no hardcoded splits."""
    if not selected:
        return []
    if len(selected) == 1:
        return [1.0]
    scores = [max(s.final_score, 1e-6) for s in selected]
    total = sum(scores)
    if total <= 0:
        return [round(1.0 / len(selected), 4)] * len(selected)
    raw = [s / total for s in scores]
    # Round and force sum to 1.0 by adjusting last
    rounded = [round(r, 4) for r in raw]
    delta = 1.0 - sum(rounded)
    if delta != 0 and rounded:
        rounded[-1] = round(rounded[-1] + delta, 4)
    return rounded


def _season_multiplier(planning_month: int | None, seasons_supported: str | None) -> float:
    """Return 0.5–1.0: penalize crops whose seasons_supported doesn't match planning month.
    Indian seasons: Kharif ~Jun–Oct, Rabi ~Nov–Apr. Month 1,2,11,12 -> Rabi; 6,7,8,9,10 -> Kharif; 3,4,5 -> Rabi (late).
    """
    if not planning_month or not seasons_supported or not (seasons_supported or "").strip():
        return 1.0
    supported = {s.strip().upper() for s in (seasons_supported or "").split(",") if s.strip()}
    if not supported:
        return 1.0
    # Map month to primary season
    if planning_month in (6, 7, 8, 9, 10):
        current = "KHARIF"
    else:
        current = "RABI"  # Jan–May, Nov–Dec
    if current in supported or "BOTH" in supported or "ALL" in supported:
        return 1.0
    if "ZAID" in supported and planning_month in (3, 4, 5):
        return 1.0
    return 0.55  # slight penalty when season not clearly supported


def _select_diverse(
    feasible: list[CropScore],
    n: int,
    category_by_id: dict[str, str],
) -> list[CropScore]:
    """Pick top-N crops while preferring category diversity.

    Strategy:
    - iterate in ranked order
    - try to pick crops from new categories first
    - if not enough, fill remaining by score order
    """
    if not feasible or n <= 0:
        return []

    selected: list[CropScore] = []
    used_categories: set[str] = set()

    for crop in feasible:
        if len(selected) >= n:
            break
        cat = category_by_id.get(crop.crop_id, "")
        if cat and cat in used_categories:
            continue
        selected.append(crop)
        if cat:
            used_categories.add(cat)

    # Fill remaining slots if category diversity couldn't fill all
    if len(selected) < n:
        selected_ids = {c.crop_id for c in selected}
        for crop in feasible:
            if len(selected) >= n:
                break
            if crop.crop_id in selected_ids:
                continue
            selected.append(crop)

    return selected


def _weighted_sum_partial(fits: dict[str, float], weights: dict[str, float]) -> float:
    """Weighted sum over intersection of dims, renormalized by used weight mass."""
    used = {k: weights[k] for k in fits.keys() if k in weights}
    denom = sum(used.values())
    if denom <= 0:
        return 0.0
    num = sum(used[k] * fits[k] for k in used)
    return float(num / denom)


def _apply_soft_penalties(base_score: float, crop_row: dict, soft_constraints: list) -> float:
    """Apply soft penalties without eliminating candidates.

    Supports: water (penalise_high_water), labour (penalise_high_labour), risk (penalise_high_risk).
    Accepts both SoftConstraint Pydantic models and plain dicts.
    """
    score = base_score
    for sc in soft_constraints:
        dim = sc.dimension if hasattr(sc, "dimension") else sc.get("dimension")
        pref = sc.preference if hasattr(sc, "preference") else sc.get("preference")
        pen = sc.penalty if hasattr(sc, "penalty") else sc.get("penalty", 0.0)
        penalty = float(pen or 0.0)
        if dim == "water" and pref == "penalise_high_water":
            if crop_row.get("water_need") == "HIGH":
                score = max(0.0, score - penalty)
        elif dim == "labour" and pref == "penalise_high_labour":
            if crop_row.get("labour_need") == "HIGH":
                score = max(0.0, score - penalty)
        elif dim == "risk" and pref == "penalise_high_risk":
            if crop_row.get("risk_level") == "HIGH":
                score = max(0.0, score - penalty)
    return score


# ── LLM layer: soft preferences from user_context ─────────────────────────

def _llm_soft_preferences(
    llm: BaseLLMClient,
    user_context: str,
    profile: ValidatedProfile,
) -> list[SoftConstraint]:
    """Derive soft constraints from user free-text context. Returns empty list on parse error."""
    system = """You are a farming advisor. Given the user's free-text context and a brief profile, output soft preferences for crop scoring as JSON.
Output a single JSON object with key "preferences": array of objects. Each object: "dimension", "preference", "penalty", "reason".
- dimension: one of "water", "labour", "risk"
- preference: "penalise_high_water" | "penalise_high_labour" | "penalise_high_risk" (only these)
- penalty: number 0.05 to 0.2 (small score deduction for matching crops)
- reason: one short sentence
Only include preferences clearly implied by the user context. If nothing relevant, return {"preferences": []}."""
    user = f"""Profile: land={profile.land_area_acres} acres, water={profile.water_availability.value}, labour={profile.labour_availability.value}, risk_tolerance={profile.risk_tolerance.value}.

User context: {user_context}

Return JSON with "preferences" array (or empty array)."""
    try:
        out = llm.complete(system, user, response_format="json")
        prefs = out.get("preferences") or []
        result: list[SoftConstraint] = []
        valid_pairs = {("water", "penalise_high_water"), ("labour", "penalise_high_labour"), ("risk", "penalise_high_risk")}
        for p in prefs if isinstance(p, dict) else []:
            dim = p.get("dimension")
            pref = p.get("preference")
            if (dim, pref) not in valid_pairs:
                continue
            penalty = float(p.get("penalty", 0.1))
            penalty = max(0.05, min(0.2, penalty))
            reason = str(p.get("reason", "From user context."))[:200]
            result.append(SoftConstraint(dimension=dim, preference=pref, penalty=penalty, reason=reason))
        return result
    except Exception as e:
        logger.warning("LLM soft preferences failed: %s", e)
        return []


def _llm_portfolio_explanation(
    llm: BaseLLMClient,
    profile: ValidatedProfile,
    weights: WeightVector,
    selected_practice: PracticeScore,
    portfolio: list[CropPortfolioEntry],
    user_context: str | None,
) -> str:
    """Generate a short human-readable explanation for the chosen crop portfolio."""
    system = """You are a farming advisor. In 1-3 short sentences, explain why this crop portfolio was chosen for this farmer. Be specific: mention crop names, area split, and how it fits their constraints and goals. Do not use bullet points."""
    crop_summary = ", ".join(f"{e.crop_name} ({e.area_fraction:.0%})" for e in portfolio)
    user = f"""Practice: {selected_practice.practice_name}. Land: {profile.land_area_acres} acres. Water: {profile.water_availability.value}, risk tolerance: {profile.risk_tolerance.value}.
Portfolio: {crop_summary}.
{f'User context: {user_context}' if user_context and (user_context or "").strip() else ''}

Write the explanation."""
    try:
        text = llm.complete_text(system, user)
        return (text or "").strip()[:500] or _deterministic_portfolio_reason(portfolio, profile)
    except Exception as e:
        logger.warning("LLM portfolio explanation failed: %s", e)
        return _deterministic_portfolio_reason(portfolio, profile)


def _deterministic_portfolio_reason(
    portfolio: list[CropPortfolioEntry],
    profile: ValidatedProfile,
) -> str:
    """Fallback explanation when LLM is disabled or fails."""
    n = len(portfolio)
    if n == 0:
        return "No feasible crops for this practice and constraints."
    if n == 1:
        return f"Selected {portfolio[0].crop_name} for best fit to your constraints and goals."
    return f"Selected {n} crops for diversification and best fit to your constraints and goals."
