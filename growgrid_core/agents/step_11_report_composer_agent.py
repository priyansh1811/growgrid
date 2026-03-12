"""Agent 11 — Report Composer Agent.

Assembles all pipeline outputs into a structured report payload:
    - Executive summary
    - Farm profile
    - Practice selection + reasoning
    - Crop portfolio + area split + grow guides
    - Agronomist verification
    - Critic review
    - Risk matrix
    - (Placeholder sections for economics, schemes, layout)
Deterministic — no LLM calls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.utils.types import (
    CriticReport,
    CropPortfolioEntry,
    GrowGuide,
    PlanRequest,
    PracticeScore,
    ReportPayload,
    ReportSection,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)


class ReportComposerAgent(BaseAgent):
    """Compose structured report payload from plan state."""

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]
        grow_guides: list[GrowGuide] = state["grow_guides"]
        warnings: list[str] = state.get("warnings", [])
        critic_report: CriticReport | None = state.get("critic_report")

        sections: list[ReportSection] = []

        # Section 1: Farm Profile
        sections.append(ReportSection(
            title="Farm Profile",
            content={
                "location": profile.location,
                "land_area_acres": profile.land_area_acres,
                "water_availability": profile.water_availability.value,
                "irrigation_source": profile.irrigation_source.value,
                "budget_total_inr": profile.budget_total_inr,
                "budget_per_acre": profile.budget_per_acre,
                "labour_availability": profile.labour_availability.value,
                "goal": profile.goal.value,
                "time_horizon_years": profile.time_horizon_years,
                "horizon_months": profile.horizon_months,
                "risk_tolerance": profile.risk_tolerance.value,
            },
        ))

        # Section 2: Practice Selection
        alternatives = state.get("practice_alternatives", [])
        sections.append(ReportSection(
            title="Recommended Practice",
            content={
                "selected": {
                    "code": practice.practice_code,
                    "name": practice.practice_name,
                    "score": round(practice.weighted_score, 3),
                },
                "alternatives": [
                    {"code": a.practice_code, "name": a.practice_name, "score": round(a.weighted_score, 3)}
                    for a in alternatives
                ],
                "reason": state.get("selected_practice_reason", ""),
            },
        ))

        # Section 3: Crop Portfolio
        sections.append(ReportSection(
            title="Crop Portfolio",
            content={
                "crops": [
                    {
                        "crop_id": c.crop_id,
                        "crop_name": c.crop_name,
                        "area_fraction": c.area_fraction,
                        "area_pct": f"{c.area_fraction:.0%}",
                        "role": c.role_hint,
                        "score": round(c.score, 3),
                    }
                    for c in portfolio
                ],
                "reason": state.get("selected_crop_portfolio_reason", ""),
            },
        ))

        # Section 4: Grow Guides
        sections.append(ReportSection(
            title="Grow Guides",
            content=[
                {
                    "crop_name": g.crop_name,
                    "sowing_window": g.sowing_window,
                    "land_prep": g.land_prep,
                    "irrigation_rules": g.irrigation_rules,
                    "fertilizer_plan": g.fertilizer_plan,
                    "pest_prevention": g.pest_prevention,
                    "harvest_notes": g.harvest_notes,
                    "why_recommended": g.why_recommended,
                    "when_not_recommended": g.when_not_recommended,
                    "monthly_timeline": g.monthly_timeline,
                }
                for g in grow_guides
            ],
        ))

        # Section 5: Verification
        verification = state.get("agronomist_verification")
        if verification:
            sections.append(ReportSection(
                title="Agronomist Verification",
                content={
                    "confidence_score": verification.confidence_score
                    if hasattr(verification, "confidence_score")
                    else verification.get("confidence_score", 0),
                    "warnings": verification.warnings
                    if hasattr(verification, "warnings")
                    else verification.get("warnings", []),
                    "required_actions": verification.required_actions
                    if hasattr(verification, "required_actions")
                    else verification.get("required_actions", []),
                },
            ))

        # Section 6: Critic Review
        if critic_report and isinstance(critic_report, CriticReport):
            sections.append(ReportSection(
                title="Consistency Review",
                content={
                    "summary": critic_report.summary,
                    "confidence": critic_report.final_confidence,
                    "issues": [
                        {
                            "severity": i.severity,
                            "dimension": i.dimension,
                            "description": i.description,
                            "fix": i.suggested_fix,
                        }
                        for i in critic_report.issues
                    ],
                },
            ))

        # Section 7: Risk Matrix
        risks: list[dict[str, str]] = []
        for w in warnings:
            risks.append({"source": "validation", "description": w})
        if critic_report and isinstance(critic_report, CriticReport):
            for issue in critic_report.issues:
                if issue.severity in ("CRITICAL", "WARNING"):
                    risks.append({
                        "source": "critic",
                        "description": issue.description,
                        "mitigation": issue.suggested_fix or "",
                    })
        sections.append(ReportSection(title="Risks & Mitigations", content=risks))

        # Build executive summary
        crop_names = ", ".join(c.crop_name for c in portfolio)
        total_area = profile.land_area_acres
        exec_summary = (
            f"For {total_area:.1f} acres in {profile.location}, "
            f"the recommended practice is {practice.practice_name} "
            f"with crops: {crop_names}. "
            f"Budget: {profile.budget_total_inr:,} INR over {profile.time_horizon_years:.1f} years."
        )
        if critic_report and isinstance(critic_report, CriticReport) and critic_report.issues:
            exec_summary += f" {critic_report.summary}"

        report = ReportPayload(
            executive_summary=exec_summary,
            sections=sections,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        state["report_payload"] = report
        logger.info("ReportComposerAgent: assembled %d sections.", len(sections))
        return state
