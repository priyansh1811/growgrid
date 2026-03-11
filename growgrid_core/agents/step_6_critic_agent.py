"""Agent 6 — Critic / Consistency Agent.

Red-teams the complete plan for contradictions:
    - water LOW but high-water crop/practice selected
    - budget mismatch (estimated cost vs budget)
    - horizon mismatch (time_to_income vs horizon)
    - labour mismatch
    - perishability gap (high perishability + no storage/market mention)
    - irrigation mismatch (NONE irrigation but needs drip/irrigation)
    - portfolio coherence (competing crops for same season/resources)
Suggests minimal fixes using already-ranked candidates.
Fully deterministic — no LLM calls.
"""

from __future__ import annotations

import logging
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.enums import IrrigationSource
from growgrid_core.utils.types import (
    CriticIssue,
    CriticReport,
    CropPortfolioEntry,
    CropScore,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)

# Severity penalties applied to confidence score
_SEVERITY_PENALTY = {"CRITICAL": 0.20, "WARNING": 0.08, "INFO": 0.02}


class CriticAgent(BaseAgent):
    """Red-team the plan for consistency issues."""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        crop_ranking: list[CropScore] = state["crop_ranking"]

        issues: list[CriticIssue] = []

        # ── Check 1: Water consistency ──────────────────────────────────
        self._check_water(profile, practice, crop_ranking, portfolio, issues)

        # ── Check 2: Budget consistency ─────────────────────────────────
        self._check_budget(profile, practice, issues)

        # ── Check 3: Horizon / time consistency ─────────────────────────
        self._check_horizon(profile, crop_ranking, portfolio, issues)

        # ── Check 4: Labour consistency ─────────────────────────────────
        self._check_labour(profile, practice, crop_ranking, portfolio, issues)

        # ── Check 5: Risk consistency ───────────────────────────────────
        self._check_risk(profile, practice, crop_ranking, portfolio, issues)

        # ── Check 6: Irrigation match ───────────────────────────────────
        self._check_irrigation(profile, practice, issues)

        # ── Check 7: Perishability gap ──────────────────────────────────
        self._check_perishability(crop_ranking, portfolio, issues)

        # ── Check 8: Portfolio coherence ────────────────────────────────
        self._check_portfolio_coherence(portfolio, issues)

        # ── Compute confidence ──────────────────────────────────────────
        confidence = 1.0
        for issue in issues:
            confidence -= _SEVERITY_PENALTY.get(issue.severity, 0.0)
        confidence = max(0.0, min(1.0, confidence))

        # ── Build summary ───────────────────────────────────────────────
        critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")
        info_count = sum(1 for i in issues if i.severity == "INFO")

        if not issues:
            summary = "No consistency issues found. The plan looks sound."
        else:
            parts = []
            if critical_count:
                parts.append(f"{critical_count} critical")
            if warning_count:
                parts.append(f"{warning_count} warning(s)")
            if info_count:
                parts.append(f"{info_count} info")
            summary = f"Found {', '.join(parts)} issue(s). Confidence: {confidence:.0%}."

        report = CriticReport(
            issues=issues,
            fixes_applied=[],
            final_confidence=confidence,
            summary=summary,
        )

        state["critic_report"] = report
        logger.info("CriticAgent: %s", summary)
        return state

    # ── Individual checks ───────────────────────────────────────────────

    def _check_water(
        self,
        profile: ValidatedProfile,
        practice: PracticeScore,
        crop_ranking: list[CropScore],
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        user_water = profile.water_availability.value
        # Check practice water fit
        water_fit = practice.fit_scores.get("water", 1.0)
        if user_water == "LOW" and water_fit < 0.4:
            issues.append(CriticIssue(
                severity="WARNING",
                dimension="water",
                description=f"Practice '{practice.practice_name}' may need more water than available (fit={water_fit:.2f}).",
                affected_item=practice.practice_code,
                suggested_fix="Consider a lower-water practice alternative.",
            ))

        # Check each crop in portfolio
        portfolio_ids = {e.crop_id for e in portfolio}
        for cs in crop_ranking:
            if cs.crop_id not in portfolio_ids or cs.eliminated:
                continue
            crop_water_fit = cs.fit_scores.get("water", 1.0)
            if user_water == "LOW" and crop_water_fit < 0.4:
                issues.append(CriticIssue(
                    severity="WARNING",
                    dimension="water",
                    description=f"Crop '{cs.crop_name}' has poor water fit ({crop_water_fit:.2f}) for LOW water availability.",
                    affected_item=cs.crop_id,
                    suggested_fix="Swap with a lower-water crop from the ranked list.",
                ))

    def _check_budget(
        self,
        profile: ValidatedProfile,
        practice: PracticeScore,
        issues: list[CriticIssue],
    ) -> None:
        capex_fit = practice.fit_scores.get("capex", 1.0)
        if capex_fit < 0.3:
            issues.append(CriticIssue(
                severity="CRITICAL",
                dimension="budget",
                description=f"Practice '{practice.practice_name}' has very low budget fit ({capex_fit:.2f}). "
                f"Budget per acre: {profile.budget_per_acre:,.0f} INR may be insufficient.",
                affected_item=practice.practice_code,
                suggested_fix="Consider a lower-cost practice or increase budget.",
            ))
        elif capex_fit < 0.5:
            issues.append(CriticIssue(
                severity="WARNING",
                dimension="budget",
                description=f"Practice '{practice.practice_name}' has marginal budget fit ({capex_fit:.2f}).",
                affected_item=practice.practice_code,
                suggested_fix="Budget is tight — ensure adequate working capital.",
            ))

    def _check_horizon(
        self,
        profile: ValidatedProfile,
        crop_ranking: list[CropScore],
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        portfolio_ids = {e.crop_id for e in portfolio}
        for cs in crop_ranking:
            if cs.crop_id not in portfolio_ids or cs.eliminated:
                continue
            time_fit_val = cs.fit_scores.get("time", 1.0)
            if time_fit_val < 0.3:
                issues.append(CriticIssue(
                    severity="CRITICAL",
                    dimension="horizon",
                    description=f"Crop '{cs.crop_name}' may not yield income within {profile.horizon_months} months (time fit={time_fit_val:.2f}).",
                    affected_item=cs.crop_id,
                    suggested_fix="Swap with a faster-maturing crop from the ranked list.",
                ))
            elif time_fit_val < 0.5:
                issues.append(CriticIssue(
                    severity="WARNING",
                    dimension="horizon",
                    description=f"Crop '{cs.crop_name}' has tight time fit ({time_fit_val:.2f}) for {profile.horizon_months}-month horizon.",
                    affected_item=cs.crop_id,
                    suggested_fix="First income may arrive close to the deadline.",
                ))

    def _check_labour(
        self,
        profile: ValidatedProfile,
        practice: PracticeScore,
        crop_ranking: list[CropScore],
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        user_labour = profile.labour_availability.value
        labour_fit = practice.fit_scores.get("labour", 1.0)
        if user_labour == "LOW" and labour_fit < 0.4:
            issues.append(CriticIssue(
                severity="WARNING",
                dimension="labour",
                description=f"Practice '{practice.practice_name}' may require more labour than available (fit={labour_fit:.2f}).",
                affected_item=practice.practice_code,
                suggested_fix="Consider mechanization or a less labour-intensive practice.",
            ))

        portfolio_ids = {e.crop_id for e in portfolio}
        for cs in crop_ranking:
            if cs.crop_id not in portfolio_ids or cs.eliminated:
                continue
            crop_labour_fit = cs.fit_scores.get("labour", 1.0)
            if user_labour == "LOW" and crop_labour_fit < 0.4:
                issues.append(CriticIssue(
                    severity="WARNING",
                    dimension="labour",
                    description=f"Crop '{cs.crop_name}' has poor labour fit ({crop_labour_fit:.2f}) for LOW availability.",
                    affected_item=cs.crop_id,
                    suggested_fix="Consider a less labour-intensive crop.",
                ))

    def _check_risk(
        self,
        profile: ValidatedProfile,
        practice: PracticeScore,
        crop_ranking: list[CropScore],
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        user_risk = profile.risk_tolerance.value
        risk_fit_val = practice.fit_scores.get("risk", 1.0)
        if user_risk == "LOW" and risk_fit_val < 0.4:
            issues.append(CriticIssue(
                severity="WARNING",
                dimension="risk",
                description=f"Practice '{practice.practice_name}' has high risk (fit={risk_fit_val:.2f}) for LOW risk tolerance.",
                affected_item=practice.practice_code,
                suggested_fix="Consider a lower-risk practice or add risk mitigation (insurance, diversification).",
            ))

        portfolio_ids = {e.crop_id for e in portfolio}
        for cs in crop_ranking:
            if cs.crop_id not in portfolio_ids or cs.eliminated:
                continue
            crop_risk_fit = cs.fit_scores.get("risk", 1.0)
            if user_risk == "LOW" and crop_risk_fit < 0.4:
                issues.append(CriticIssue(
                    severity="WARNING",
                    dimension="risk",
                    description=f"Crop '{cs.crop_name}' has high risk (fit={crop_risk_fit:.2f}) for LOW tolerance.",
                    affected_item=cs.crop_id,
                    suggested_fix="Consider crop insurance or a safer alternative.",
                ))

    def _check_irrigation(
        self,
        profile: ValidatedProfile,
        practice: PracticeScore,
        issues: list[CriticIssue],
    ) -> None:
        if profile.irrigation_source == IrrigationSource.NONE:
            # Protected cultivation (polyhouse, net_house, hydroponics) needs irrigation
            protected_codes = {"POLYHOUSE", "NET_HOUSE", "HYDROPONICS"}
            if practice.practice_code in protected_codes:
                issues.append(CriticIssue(
                    severity="CRITICAL",
                    dimension="irrigation",
                    description=f"Practice '{practice.practice_name}' requires irrigation but source is NONE.",
                    affected_item=practice.practice_code,
                    suggested_fix="Install irrigation before adopting this practice.",
                ))
            elif practice.practice_code in {"DRIP_INTENSIVE", "DRIP_MULCH"}:
                issues.append(CriticIssue(
                    severity="CRITICAL",
                    dimension="irrigation",
                    description=f"Practice '{practice.practice_name}' requires drip irrigation but source is NONE.",
                    affected_item=practice.practice_code,
                    suggested_fix="Set up drip irrigation infrastructure first.",
                ))

    def _check_perishability(
        self,
        crop_ranking: list[CropScore],
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        if len(portfolio) == 1:
            issues.append(CriticIssue(
                severity="INFO",
                dimension="perishability",
                description="Single-crop portfolio — consider diversification to reduce post-harvest risk.",
                affected_item=portfolio[0].crop_id,
                suggested_fix="If land allows, add a second crop for risk hedging.",
            ))

    def _check_portfolio_coherence(
        self,
        portfolio: list[CropPortfolioEntry],
        issues: list[CriticIssue],
    ) -> None:
        if len(portfolio) < 2:
            return

        # Check for very uneven splits that might not justify the complexity
        for entry in portfolio:
            if entry.area_fraction < 0.10:
                issues.append(CriticIssue(
                    severity="INFO",
                    dimension="portfolio",
                    description=f"Crop '{entry.crop_name}' has only {entry.area_fraction:.0%} area share — "
                    "may not be worth the operational overhead.",
                    affected_item=entry.crop_id,
                    suggested_fix="Consider dropping this crop or increasing its share.",
                ))
