"""Agent 10 — Government Schemes Agent.

Retrieves relevant government schemes using tag-matching (MVP approach).
Matches schemes by user location (state), selected practice, crop categories,
farmer category (SC/ST/OBC/General), land size, and season awareness.
Ranks by multi-dimensional relevance score.
No vector DB / RAG required — uses structured metadata from schemes_metadata table.
Fully deterministic — no LLM calls.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import get_all_schemes, get_crop_by_id
from growgrid_core.utils.location import parse_state_from_location
from growgrid_core.utils.types import (
    CropPortfolioEntry,
    MatchedScheme,
    PlanRequest,
    PracticeScore,
    SchemesReport,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)

_MAX_RESULTS = 15

# Category mapping from user input to tag format
_CATEGORY_MAP = {"general": "GENERAL", "obc": "OBC", "sc": "SC", "st": "ST"}

# Month → season mapping for season-aware scoring
_MONTH_TO_SEASON: dict[int, str] = {
    1: "RABI", 2: "RABI", 3: "RABI",
    4: "ZAID", 5: "ZAID",
    6: "KHARIF", 7: "KHARIF", 8: "KHARIF", 9: "KHARIF",
    10: "RABI", 11: "RABI", 12: "RABI",
}


def _planning_month_to_season(planning_month: int | None) -> str | None:
    """Convert a planning month (1-12) to a season string."""
    if not planning_month or planning_month < 1 or planning_month > 12:
        return None
    return _MONTH_TO_SEASON.get(planning_month)


def _derive_farmer_type(land_area_acres: float) -> str:
    """Classify farmer by land holding size per Indian norms."""
    if land_area_acres <= 2.5:
        return "MARGINAL"
    elif land_area_acres <= 5.0:
        return "SMALL"
    else:
        return "OTHER"


def _build_scheme_checklist(
    scheme: dict, user_state: str, user_cat: str
) -> list[str]:
    """Build per-scheme action items instead of a generic checklist."""
    items: list[str] = []

    # Basic document readiness
    items.append("Keep Aadhaar-linked bank passbook and land ownership/lease documents ready")

    # Application method
    app_url = scheme.get("application_url")
    if app_url:
        items.append(f"Apply online at: {app_url}")
    else:
        items.append("Contact your local agriculture/horticulture department office to apply")

    # State-specific guidance
    scheme_state = scheme.get("state", "ALL")
    if scheme_state != "ALL":
        items.append(f"Visit {user_state} state agriculture department or district collectorate for assistance")
    else:
        items.append("Available nationwide — apply through your nearest agriculture office or Common Service Centre (CSC)")

    # Category-specific documents
    if user_cat in ("SC", "ST"):
        items.append("Keep caste certificate ready for higher subsidy rate eligibility")
    elif user_cat == "OBC":
        items.append("Keep OBC certificate ready if required for eligibility verification")

    # Season-specific timing
    season_window = scheme.get("season_window") or ""
    if season_window:
        items.append(f"Check application window — scheme is active for: {season_window.replace(';', ', ')} season(s)")

    # Land document note for land-ceiling schemes
    max_land = scheme.get("max_land_acres")
    if max_land:
        items.append(f"Land holding must be ≤ {max_land} acres — keep land records for verification")

    return items


def _build_category_subsidy_note(
    scheme: dict, user_cat: str, subsidy_pct: float
) -> str | None:
    """Generate a note about category-specific subsidy advantages."""
    if subsidy_pct <= 0:
        return None

    gender_bonus = scheme.get("gender_bonus_pct") or 0

    if user_cat in ("SC", "ST"):
        # Most Indian schemes offer 10-20% higher subsidy for SC/ST
        enhanced_pct = min(subsidy_pct + 15, 100)  # typical 15% enhancement
        note = f"As a {user_cat} farmer, you may be eligible for an enhanced subsidy of up to {enhanced_pct:.0f}% (vs {subsidy_pct:.0f}% for General category)"
        if gender_bonus > 0:
            note += f". Women farmers may get an additional {gender_bonus:.0f}% bonus"
        return note
    elif user_cat == "OBC":
        enhanced_pct = min(subsidy_pct + 10, 100)
        return f"As an OBC farmer, you may be eligible for a subsidy of up to {enhanced_pct:.0f}% (vs {subsidy_pct:.0f}% for General category)"
    elif gender_bonus > 0:
        return f"Women farmers may get an additional {gender_bonus:.0f}% bonus subsidy"

    return None


class GovtSchemesAgent(BaseAgent):
    """Retrieve relevant government schemes via tag matching."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]

        # ── Extract user context ────────────────────────────────────────
        user_state = parse_state_from_location(profile.location) or profile.location.strip()
        practice_code = practice.practice_code
        user_cat = _CATEGORY_MAP.get((getattr(profile, "category", None) or "general").lower(), "GENERAL")
        farmer_type = _derive_farmer_type(profile.land_area_acres)
        planning_month = getattr(profile, "planning_month", None)
        planning_season = _planning_month_to_season(planning_month)

        # Gather crop categories for matching
        crop_categories: set[str] = set()
        crop_ids: set[str] = set()
        for entry in portfolio:
            crop_ids.add(entry.crop_id)
            crop_info = get_crop_by_id(conn, entry.crop_id)
            if crop_info:
                cat = crop_info.get("category", "")
                if cat:
                    crop_categories.add(cat)

        # ── Load all schemes and score each ─────────────────────────────
        all_schemes = get_all_schemes(conn)
        scored: list[tuple[float, dict, list[str]]] = []

        for scheme in all_schemes:
            score = 0.0
            reasons: list[str] = []

            # ── 1. State match (gate) ───────────────────────────────────
            scheme_state = scheme.get("state", "ALL")
            if scheme_state == "ALL":
                score += 1.0
                reasons.append("Central government scheme (applies to all states)")
            elif user_state.lower() in scheme_state.lower():
                score += 2.0
                reasons.append(f"Applicable in {user_state}")
                # Bonus for state-specific schemes — they are more actionable
                score += 1.5
                reasons.append(f"State-specific scheme for {user_state} — higher relevance")
            else:
                continue  # Skip schemes not applicable to user's state

            # ── 2. Land size eligibility (gate) ─────────────────────────
            max_land = scheme.get("max_land_acres")
            if max_land and max_land > 0 and profile.land_area_acres > max_land:
                continue  # Farmer's land exceeds scheme ceiling — not eligible

            # ── 3. Farmer type targeting ────────────────────────────────
            farmer_type_tags_raw = scheme.get("farmer_type_tags") or ""
            farmer_type_tags = {t.strip() for t in farmer_type_tags_raw.split(";") if t.strip()}
            if farmer_type_tags and "ALL" not in farmer_type_tags:
                if farmer_type in farmer_type_tags:
                    score += 1.0
                    reasons.append(f"Targeted for {farmer_type.lower()} farmers")
                # Don't skip even if not targeted — scheme may still apply
            elif "ALL" in farmer_type_tags:
                score += 0.3
                reasons.append("Open to all farmer categories")

            # ── 4. Category-based scoring ───────────────────────────────
            category_tags_raw = scheme.get("category_tags", "") or ""
            category_tags = {t.strip() for t in category_tags_raw.split(";") if t.strip()}
            if category_tags and "ALL" not in category_tags:
                if user_cat in category_tags:
                    score += 0.5
                    reasons.append(f"Available for {user_cat} category")
            # SC/ST bonus — most schemes offer higher subsidy rates
            subsidy_pct = scheme.get("subsidy_pct") or 0
            if user_cat in ("SC", "ST") and subsidy_pct > 0:
                score += 1.0
                reasons.append(f"Higher subsidy rate likely for {user_cat} category")

            # ── 5. Practice tag match ───────────────────────────────────
            practice_tags_raw = scheme.get("practice_tags", "") or ""
            practice_tags = {t.strip() for t in practice_tags_raw.split(";") if t.strip()}
            if practice_code in practice_tags:
                score += 2.0
                reasons.append(f"Matches selected practice: {practice_code}")
            elif "ALL" in practice_tags:
                score += 0.5
                reasons.append("Applicable to all practices")
            else:
                # Partial match (e.g., DRIP_INTENSIVE matches DRIP schemes)
                for tag in practice_tags:
                    if tag in practice_code or practice_code in tag:
                        score += 1.0
                        reasons.append(f"Partially matches practice via tag: {tag}")
                        break

            # ── 6. Crop tag match ───────────────────────────────────────
            crop_tags_raw = scheme.get("crop_tags", "") or ""
            crop_tags = {t.strip() for t in crop_tags_raw.split(";") if t.strip()}
            if "ALL" in crop_tags:
                score += 0.5
                reasons.append("Applicable to all crops")
            else:
                matched_cats = crop_categories & crop_tags
                if matched_cats:
                    score += 1.5
                    reasons.append(f"Matches crop categories: {', '.join(matched_cats)}")

            # ── 7. Season-aware scoring ─────────────────────────────────
            season_window_raw = scheme.get("season_window") or ""
            if season_window_raw and planning_season:
                season_tags = {t.strip() for t in season_window_raw.split(";") if t.strip()}
                if planning_season in season_tags:
                    score += 0.5
                    reasons.append(f"Available in {planning_season} season")

            # ── 8. Subsidy value bonus ──────────────────────────────────
            max_subsidy = scheme.get("max_subsidy_inr") or 0
            if subsidy_pct > 0:
                score += 0.3
            if max_subsidy > 0:
                score += 0.2

            scored.append((score, scheme, reasons))

        # ── Sort by score descending, take top N ────────────────────────
        scored.sort(key=lambda x: x[0], reverse=True)
        top_schemes = scored[:_MAX_RESULTS]

        # ── Build output ────────────────────────────────────────────────
        matched: list[MatchedScheme] = []
        total_potential_subsidy = 0.0
        schemes_by_type: dict[str, list[str]] = {}
        state_specific_count = 0
        central_count = 0

        for score_val, scheme, reasons in top_schemes:
            max_sub = scheme.get("max_subsidy_inr") or 0
            sub_pct = scheme.get("subsidy_pct") or 0
            if max_sub > 0:
                total_potential_subsidy += max_sub

            scheme_id = scheme["scheme_id"]
            scheme_type = scheme.get("scheme_type") or "OTHER"
            scheme_state = scheme.get("state", "ALL")

            # Track state vs central counts
            if scheme_state == "ALL":
                central_count += 1
            else:
                state_specific_count += 1

            # Group by type
            schemes_by_type.setdefault(scheme_type, []).append(scheme_id)

            # Build per-scheme checklist
            checklist_items = _build_scheme_checklist(scheme, user_state, user_cat)

            # Build category subsidy note
            category_note = _build_category_subsidy_note(scheme, user_cat, sub_pct)

            matched.append(MatchedScheme(
                scheme_id=scheme_id,
                scheme_name=scheme["scheme_name"],
                relevance_score=round(score_val, 2),
                subsidy_pct=scheme.get("subsidy_pct"),
                max_subsidy_inr=scheme.get("max_subsidy_inr"),
                eligibility_summary=scheme.get("eligibility_summary", ""),
                application_url=scheme.get("application_url"),
                match_reasons=reasons,
                scheme_type=scheme_type,
                checklist_items=checklist_items,
                category_subsidy_note=category_note,
                source_url=scheme.get("source_url"),
            ))

        # Global eligibility checklist (high-level, supplements per-scheme checklists)
        checklist = [
            "Ensure Aadhaar is linked to bank account for Direct Benefit Transfer (DBT)",
            "Keep land ownership/lease documents (7/12 extract, khatauni) ready",
            f"Verify eligibility at local agriculture office in {user_state}",
            "Check application deadlines for the current season",
        ]
        if user_cat in ("SC", "ST"):
            checklist.append("Keep valid caste certificate for enhanced subsidy eligibility")
        if farmer_type in ("MARGINAL", "SMALL"):
            checklist.append(f"As a {farmer_type.lower()} farmer (≤ {5 if farmer_type == 'SMALL' else 2.5} acres), you may qualify for priority under many schemes")

        report = SchemesReport(
            matched_schemes=matched,
            total_potential_subsidy=total_potential_subsidy if total_potential_subsidy > 0 else None,
            eligibility_checklist=checklist,
            data_note="Based on scheme data as of Jan 2025. Verify current eligibility and deadlines with local authorities or at https://agriwelfare.gov.in.",
            schemes_by_type=schemes_by_type,
            state_specific_count=state_specific_count,
            central_count=central_count,
        )

        state["schemes"] = report
        logger.info(
            "GovtSchemesAgent: matched %d schemes (%d state, %d central) for %s (%s, %s farmer).",
            len(matched), state_specific_count, central_count,
            user_state, user_cat, farmer_type,
        )
        return state
