"""LLM-powered sanity checker for Economist agent outputs.

Reviews deterministic CAPEX, OPEX, revenue, profit, break-even, and ROI
and flags unrealistic, suspicious, or inconsistent values.

NEVER overrides or modifies the deterministic calculations.
Only flags, explains, and suggests corrected interpretation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from growgrid_core.tools.llm_client import BaseLLMClient

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an agricultural economics expert reviewing a farm plan's financial projections for India.

You will receive computed economic data for a farming plan. Your job is to:
1. Check whether CAPEX per acre is realistic for the crop type and practice
2. Check whether OPEX per acre is reasonable
3. Check whether revenue per acre aligns with known market data for India
4. Check whether total ROI, annualized ROI, capital requirement, and break-even time are realistic
5. Check whether profit margins make sense for the crop and region
6. Detect any suspicious outliers, impossible values, or internal inconsistencies

Rules:
- NEVER invent or provide alternative numbers unless flagging a clear issue
- NEVER silently correct anything — only FLAG and EXPLAIN
- For each check, give status: "OK", "WARNING", or "SUSPICIOUS"
- Be specific about what looks wrong and why
- Consider Indian agricultural economics context (INR values, Indian crop yields, Indian market prices)
- A CAPEX of ₹0 for any crop is suspicious
- ROI above 200% for annual crops is unusual and should be flagged
- Annualized ROI above 60% should be treated cautiously unless the crop is very short-cycle and high value
- Break-even under 3 months for non-vegetable crops is suspicious
- OPEX below ₹5,000/acre for any crop is unusually low

Respond ONLY with valid JSON in this exact format:
{
  "overall_status": "PASSED" | "WARNINGS" | "FAILED",
  "checks": [
    {
      "field": "<what was checked>",
      "status": "OK" | "WARNING" | "SUSPICIOUS",
      "message": "<explanation>"
    }
  ],
  "summary": "<1-2 sentence overall assessment>"
}
"""


def run_sanity_check(
    llm_client: BaseLLMClient | None,
    economics_data: dict[str, Any],
    crop_names: list[str],
    practice_name: str,
    land_acres: float,
    labour_availability: str,
    irrigation_source: str,
) -> dict[str, Any]:
    """Run LLM sanity check on deterministic economic outputs.

    Args:
        llm_client: LLM client (can be None if no API key).
        economics_data: Dict with cost_breakdown, roi_summary, sensitivity, totals.
        crop_names: List of crop names in portfolio.
        practice_name: Selected practice name.
        land_acres: Total land area.
        labour_availability: LOW/MED/HIGH.
        irrigation_source: Irrigation type.

    Returns:
        Dict with overall_status, checks[], and summary.
        Falls back to a basic rule-based check if LLM is unavailable.
    """
    if llm_client is None:
        return _rule_based_fallback(economics_data)

    user_prompt = _build_user_prompt(
        economics_data, crop_names, practice_name,
        land_acres, labour_availability, irrigation_source,
    )

    try:
        result = llm_client.complete(_SYSTEM_PROMPT, user_prompt, response_format="json")
        # Validate response structure
        if not isinstance(result, dict):
            logger.warning("Sanity checker returned non-dict: %s", type(result))
            return _rule_based_fallback(economics_data)
        if "overall_status" not in result:
            result["overall_status"] = "WARNINGS"
        if "checks" not in result:
            result["checks"] = []
        if "summary" not in result:
            result["summary"] = "Sanity check completed."
        return result
    except Exception:
        logger.exception("LLM sanity check failed, falling back to rule-based")
        return _rule_based_fallback(economics_data)


def _build_user_prompt(
    econ: dict[str, Any],
    crop_names: list[str],
    practice: str,
    land: float,
    labour: str,
    irrigation: str,
) -> str:
    """Build the user prompt with economic data summary."""
    lines = [
        "Review these farm economics projections:",
        f"",
        f"Practice: {practice}",
        f"Crops: {', '.join(crop_names)}",
        f"Land: {land} acres",
        f"Labour availability: {labour}",
        f"Irrigation: {irrigation}",
        f"",
        f"Total CAPEX: ₹{econ.get('total_capex', 0):,.0f}",
        f"Total OPEX (annual): ₹{econ.get('total_annual_opex', 0):,.0f}",
        f"",
        "Cost breakdown per crop (per acre):",
    ]

    for cb in econ.get("cost_breakdown", []):
        lines.append(
            f"  {cb.get('crop_name', '?')}: "
            f"CAPEX ₹{cb.get('capex_per_acre', 0):,.0f}/acre, "
            f"OPEX ₹{cb.get('opex_per_acre', 0):,.0f}/acre"
        )

    lines.append("")
    lines.append("ROI scenarios:")
    for roi in econ.get("roi_summary", []):
        lines.append(
            f"  {roi.get('scenario', '?')}: "
            f"Revenue ₹{roi.get('revenue', 0):,.0f}, "
            f"Profit ₹{roi.get('profit', 0):,.0f}, "
            f"ROI {roi.get('roi_pct', 0):.1f}%, "
            f"Annualized ROI {roi.get('annualized_roi_pct', 0):.1f}%, "
            f"Capital required ₹{roi.get('capital_required', 0):,.0f}, "
            f"Peak cash deficit ₹{roi.get('peak_cash_deficit', 0):,.0f}, "
            f"Payback status {roi.get('payback_status', 'UNKNOWN')}, "
            f"Break-even {roi.get('breakeven_months', 'N/A')} months"
        )

    lines.append("")
    lines.append(f"Data coverage: {econ.get('data_coverage', 0) * 100:.0f}%")

    return "\n".join(lines)


def _rule_based_fallback(econ: dict[str, Any]) -> dict[str, Any]:
    """Basic rule-based sanity check when LLM is unavailable.

    Without full LLM context, the fallback only issues warnings — never
    SUSPICIOUS/FAILED — to avoid false alarms on data that might be
    perfectly valid for the specific crop, practice, or region.
    """
    checks: list[dict[str, str]] = []
    has_warning = False

    total_capex = econ.get("total_capex", 0)
    total_opex = econ.get("total_annual_opex", 0) or econ.get("total_opex", 0)

    # Check: zero CAPEX
    if total_capex == 0:
        checks.append({
            "field": "total_capex",
            "status": "WARNING",
            "message": "Total CAPEX is ₹0. This may indicate missing cost data, or a low-investment practice.",
        })
        has_warning = True
    else:
        checks.append({"field": "total_capex", "status": "OK", "message": "CAPEX is non-zero."})

    # Check: very low OPEX
    if total_opex > 0 and total_opex < 5000:
        checks.append({
            "field": "total_annual_opex",
            "status": "WARNING",
            "message": f"Annual OPEX (₹{total_opex:,.0f}) seems very low. Verify input costs.",
        })
        has_warning = True
    elif total_opex > 0:
        checks.append({"field": "total_annual_opex", "status": "OK", "message": "OPEX is within expected range."})

    # Check: ROI
    for roi in econ.get("roi_summary", []):
        scenario = roi.get("scenario", "")
        roi_pct = roi.get("roi_pct", 0)
        annualized_roi = roi.get("annualized_roi_pct", 0)
        if roi_pct > 300:
            checks.append({
                "field": f"roi_{scenario}",
                "status": "WARNING",
                "message": f"{scenario.capitalize()} ROI of {roi_pct:.1f}% is very high. Verify yield and price data.",
            })
            has_warning = True
        elif annualized_roi > 60:
            checks.append({
                "field": f"annualized_roi_{scenario}",
                "status": "WARNING",
                "message": f"{scenario.capitalize()} annualized ROI of {annualized_roi:.1f}% is aggressive. Validate price, yield, and turnover assumptions.",
            })
            has_warning = True
        elif roi_pct < -50:
            checks.append({
                "field": f"roi_{scenario}",
                "status": "WARNING",
                "message": f"{scenario.capitalize()} ROI of {roi_pct:.1f}% indicates significant loss.",
            })
            has_warning = True

    # Check: break-even
    for roi in econ.get("roi_summary", []):
        be = roi.get("breakeven_months")
        payback_status = roi.get("payback_status")
        if be is not None and be < 1:
            checks.append({
                "field": f"breakeven_{roi.get('scenario', '')}",
                "status": "WARNING",
                "message": "Break-even under 1 month is unusual for most crops.",
            })
            has_warning = True
        elif payback_status in {"BEYOND_HORIZON", "NOT_PROFITABLE"}:
            checks.append({
                "field": f"breakeven_{roi.get('scenario', '')}",
                "status": "WARNING",
                "message": f"Payback status is {payback_status.lower().replace('_', ' ')}. Review the cashflow timeline carefully.",
            })
            has_warning = True

    # Check: data coverage
    coverage = econ.get("data_coverage", 0)
    if coverage < 0.5:
        checks.append({
            "field": "data_coverage",
            "status": "WARNING",
            "message": f"Only {coverage * 100:.0f}% of crops have detailed cost data. Results may be approximate.",
        })
        has_warning = True

    # Check: per-crop CAPEX
    for cb in econ.get("cost_breakdown", []):
        capex_pa = cb.get("capex_per_acre", 0)
        if capex_pa == 0:
            checks.append({
                "field": f"capex_{cb.get('crop_name', '?')}",
                "status": "WARNING",
                "message": f"CAPEX for {cb.get('crop_name', '?')} is ₹0/acre. May be missing cost data.",
            })
            has_warning = True

    overall = "WARNINGS" if has_warning else "PASSED"

    issue_count = sum(1 for c in checks if c["status"] != "OK")
    return {
        "overall_status": overall,
        "checks": checks,
        "summary": (
            "Rule-based sanity check completed (LLM unavailable). "
            + (f"Found {issue_count} item(s) to review." if issue_count else "No issues found.")
        ),
    }
