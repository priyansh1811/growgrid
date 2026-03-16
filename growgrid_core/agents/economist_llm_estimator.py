"""LLM fallback helpers for the economist agent.

Used only when structured crop/practice cost data is missing.
"""

from __future__ import annotations

from typing import Any

from growgrid_core.tools.llm_client import BaseLLMClient

_SYSTEM_PROMPT = """\
You are an Indian agricultural finance analyst.

Estimate realistic per-acre farm economics for the specified crop and farming practice.
Return conservative but practical values in INR, suitable for farm planning in India.

Rules:
- Prefer realistic mid-market values, not optimistic headline numbers
- CAPEX must include setup and establishment investment before normal operations
- annual_opex_per_acre must include recurring input, labour, irrigation, protection, and harvest handling costs
- Keep estimates internally consistent with the crop type, practice type, irrigation, labour intensity, and time to first income
- Respond only as valid JSON

JSON schema:
{
  "capex_per_acre": number,
  "annual_opex_per_acre": number,
  "rationale": "short explanation"
}
"""


def estimate_crop_costs_with_llm(
    llm_client: BaseLLMClient | None,
    *,
    crop_name: str,
    practice_code: str,
    crop_info: dict[str, Any] | None,
    land_total_acres: float,
    irrigation_source: str,
    water_availability: str,
    labour_availability: str,
    horizon_months: int,
) -> dict[str, Any] | None:
    """Estimate missing crop costs when the knowledge base has no structured rows."""
    if llm_client is None:
        return None

    crop_category = (crop_info or {}).get("category", "UNKNOWN")
    labour_need = (crop_info or {}).get("labour_need", "MED")
    water_need = (crop_info or {}).get("water_need", "MED")
    risk_level = (crop_info or {}).get("risk_level", "MED")
    income_min = (crop_info or {}).get("time_to_first_income_months_min", 0) or 0
    income_max = (crop_info or {}).get("time_to_first_income_months_max", 0) or 0

    user_prompt = "\n".join(
        [
            f"Crop: {crop_name}",
            f"Category: {crop_category}",
            f"Practice code: {practice_code}",
            f"Farm size: {land_total_acres:.2f} acres",
            f"Irrigation source: {irrigation_source}",
            f"Water availability: {water_availability}",
            f"Farmer labour availability: {labour_availability}",
            f"Crop labour need: {labour_need}",
            f"Crop water need: {water_need}",
            f"Crop risk level: {risk_level}",
            f"Time to first income: {income_min}-{income_max} months",
            f"Planning horizon: {horizon_months} months",
            "",
            "Provide a realistic per-acre capex and annual opex estimate.",
        ]
    )

    try:
        result = llm_client.complete(_SYSTEM_PROMPT, user_prompt, response_format="json")
    except Exception:
        return None

    if not isinstance(result, dict):
        return None

    capex = float(result.get("capex_per_acre", 0) or 0)
    opex = float(result.get("annual_opex_per_acre", 0) or 0)
    if capex <= 0 or opex <= 0:
        return None

    return {
        "capex_per_acre": capex,
        "annual_opex_per_acre": opex,
        "rationale": str(result.get("rationale", "") or "").strip(),
    }
