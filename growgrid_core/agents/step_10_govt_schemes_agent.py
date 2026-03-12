"""Agent 10 — Government Schemes Agent.

Retrieves relevant government schemes using tag-matching (MVP approach).
Matches schemes by user location (state), selected practice, crop categories,
and ranks by tag overlap relevance score.
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
from growgrid_core.utils.types import (
    CropPortfolioEntry,
    MatchedScheme,
    PlanRequest,
    PracticeScore,
    SchemesReport,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)

_MAX_RESULTS = 10


class GovtSchemesAgent(BaseAgent):
    """Retrieve relevant government schemes via tag matching."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]

        # Extract user's state from location (first word or full string)
        user_state = profile.location.strip().split(",")[0].strip().split()[0].strip()
        practice_code = practice.practice_code

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

        # Load all schemes and score each
        all_schemes = get_all_schemes(conn)
        scored: list[tuple[float, dict, list[str]]] = []

        for scheme in all_schemes:
            score = 0.0
            reasons: list[str] = []

            # State match
            scheme_state = scheme.get("state", "ALL")
            if scheme_state == "ALL":
                score += 1.0
                reasons.append("Central government scheme (applies to all states)")
            elif user_state.lower() in scheme_state.lower():
                score += 2.0
                reasons.append(f"Applicable in {user_state}")
            else:
                continue  # Skip schemes not applicable to user's state

            # Practice tag match
            practice_tags_raw = scheme.get("practice_tags", "") or ""
            practice_tags = {t.strip() for t in practice_tags_raw.split(";") if t.strip()}
            if practice_code in practice_tags:
                score += 2.0
                reasons.append(f"Matches selected practice: {practice_code}")
            elif "ALL" in practice_tags:
                score += 0.5
                reasons.append("Applicable to all practices")
            else:
                # Check for partial match (e.g., DRIP_INTENSIVE matches DRIP schemes)
                for tag in practice_tags:
                    if tag in practice_code or practice_code in tag:
                        score += 1.0
                        reasons.append(f"Partially matches practice via tag: {tag}")
                        break

            # Crop tag match
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

            # Subsidy value bonus (higher subsidy = more relevant)
            subsidy_pct = scheme.get("subsidy_pct") or 0
            max_subsidy = scheme.get("max_subsidy_inr") or 0
            if subsidy_pct > 0:
                score += 0.3
            if max_subsidy > 0:
                score += 0.2

            scored.append((score, scheme, reasons))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: x[0], reverse=True)
        top_schemes = scored[:_MAX_RESULTS]

        # Build output
        matched: list[MatchedScheme] = []
        total_potential_subsidy = 0.0

        for score, scheme, reasons in top_schemes:
            max_sub = scheme.get("max_subsidy_inr") or 0
            if max_sub > 0:
                total_potential_subsidy += max_sub

            matched.append(MatchedScheme(
                scheme_id=scheme["scheme_id"],
                scheme_name=scheme["scheme_name"],
                relevance_score=round(score, 2),
                subsidy_pct=scheme.get("subsidy_pct"),
                max_subsidy_inr=scheme.get("max_subsidy_inr"),
                eligibility_summary=scheme.get("eligibility_summary", ""),
                application_url=scheme.get("application_url"),
                match_reasons=reasons,
            ))

        # Build eligibility checklist
        checklist = [
            "Ensure Aadhaar is linked to bank account",
            "Keep land ownership/lease documents ready",
            f"Verify eligibility at local agriculture office for {user_state}",
            "Check application deadlines for the current season",
        ]

        report = SchemesReport(
            matched_schemes=matched,
            total_potential_subsidy=total_potential_subsidy if total_potential_subsidy > 0 else None,
            eligibility_checklist=checklist,
            data_note="Based on scheme data as of Jan 2025. Verify current eligibility and deadlines with local authorities.",
        )

        state["schemes"] = report
        logger.info("GovtSchemesAgent: matched %d schemes for %s.", len(matched), user_state)
        return state
