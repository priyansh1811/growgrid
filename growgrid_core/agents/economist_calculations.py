"""Economic calculation engine for the Economist agent.

The model is primarily knowledge-base driven:
- crop-level cost/yield/price bands
- practice-level cost profiles
- practice-level scenario calibration
- crop timing, risk, perishability, labour, and water metadata

When structured cost data is genuinely missing, an LLM can be used as a
strict fallback estimator for per-acre CAPEX and annual OPEX.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from growgrid_core.agents.economist_llm_estimator import estimate_crop_costs_with_llm
from growgrid_core.db.queries import (
    get_crop_by_id,
    get_crop_costs,
    get_crop_labour_share,
    get_economics_scenario_reference,
    get_fertilizer_input_costs,
    get_icar_nutrient_plan,
    get_irrigation_costs,
    get_loss_factor,
    get_practice_costs,
    get_price_bands,
    get_yield_bands,
)
from growgrid_core.tools.llm_client import BaseLLMClient
from growgrid_core.utils.icar_matching import match_id_to_icar_names, normalize_state_for_icar
from growgrid_core.utils.season import detect_season

logger = logging.getLogger(__name__)

_LABOUR_MULTIPLIER: dict[tuple[str, str], float] = {
    ("LOW", "LOW"): 1.0,
    ("LOW", "MED"): 1.20,
    ("LOW", "HIGH"): 1.45,
    ("MED", "LOW"): 0.90,
    ("MED", "MED"): 1.0,
    ("MED", "HIGH"): 1.15,
    ("HIGH", "LOW"): 0.80,
    ("HIGH", "MED"): 0.85,
    ("HIGH", "HIGH"): 1.0,
}

_IRRIGATION_CAPEX_PER_ACRE: dict[str, float] = {
    "NONE": 0,
    "CANAL": 2_000,
    "BOREWELL": 15_000,
    "DRIP": 25_000,
    "MIXED": 18_000,
}

_IRRIGATION_OPEX_PER_ACRE: dict[str, float] = {
    "NONE": 0,
    "CANAL": 1_500,
    "BOREWELL": 4_000,
    "DRIP": 2_500,
    "MIXED": 3_000,
}

_WATER_OPEX_MULTIPLIER: dict[str, float] = {
    "LOW": 1.30,
    "MED": 1.0,
    "HIGH": 0.85,
}

_DEFAULT_SCENARIO_REFERENCE: dict[str, float] = {
    "capital_buffer_floor_months": 3.0,
    "capex_contingency_pct": 0.05,
    "best_case_opex_multiplier": 0.98,
    "base_case_opex_multiplier": 1.0,
    "worst_case_opex_multiplier": 1.12,
}

_SEASON_START_MONTH: dict[str, int] = {
    "ZAID": 3,
    "KHARIF": 6,
    "RABI": 11,
}

# Year-wise yield ramp for tree crops (fraction of full yield).
# Different crops reach bearing maturity at very different rates:
# - FAST: papaya, banana, drumstick — bear within year 1
# - MEDIUM: guava, lemon, dragonfruit — 2-4 years to full yield
# - SLOW: mango, coconut, cashew — 5-7+ years to full yield
_TREE_CROP_RAMPS: dict[str, tuple[float, ...]] = {
    "FAST":    (0.60, 0.85, 1.0),
    "MEDIUM":  (0.40, 0.65, 0.85, 1.0),
    "SLOW":    (0.10, 0.25, 0.45, 0.65, 0.80, 0.95, 1.0),
    "DEFAULT": (0.40, 0.65, 0.85, 1.0),
}

_CROP_RAMP_CATEGORY: dict[str, str] = {
    "FR_PAPAYA": "FAST",
    "FR_BANANA": "FAST",
    "FR_DRUMSTICK": "FAST",
    "FR_GUAVA": "MEDIUM",
    "FR_LEMON": "MEDIUM",
    "FR_ACID_LIME": "MEDIUM",
    "FR_DRAGONFRUIT": "MEDIUM",
    "FR_POMEGRANATE": "MEDIUM",
    "FR_MANGO": "SLOW",
    "FR_COCONUT": "SLOW",
    "FR_CASHEW": "SLOW",
    "FR_ARECANUT": "SLOW",
    "FR_SAPOTA": "SLOW",
}

# Keep backward-compatible alias
_TREE_CROP_RAMP: tuple[float, ...] = _TREE_CROP_RAMPS["DEFAULT"]


def _get_tree_ramp(crop_id: str) -> tuple[float, ...]:
    """Return the yield ramp tuple for a tree/perennial crop."""
    cat = _CROP_RAMP_CATEGORY.get(crop_id, "DEFAULT")
    return _TREE_CROP_RAMPS.get(cat, _TREE_CROP_RAMPS["DEFAULT"])

_KEYWORD_FAMILIES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("seed", "seedling", "sapling", "planting material", "transplant", "fingerling", "spawn", "colony", "chicks", "birds", "livestock", "mother plant"), "planting_material"),
    (("land preparation", "land prep", "pit digging", "bed prep", "beds", "soil testing", "amendment", "excavation", "lining", "flooring"), "site_preparation"),
    (("drip", "irrigation", "water storage", "water inlet", "water outlet", "pump", "filter", "fertigation", "tank", "water trough"), "irrigation_system"),
    (("structure", "frame", "poly film", "shade net", "shed", "room setup", "channels", "racks", "benching", "grow bags", "trays setup", "pond excavation"), "structure"),
    (("ventilation", "climate control", "humidity", "temperature control", "monitoring", "sensor", "power backup", "insect net"), "support_systems"),
    (("tool", "equipment", "gear", "extractor", "crate", "storage", "tray", "bag", "sprayer"), "tools_equipment"),
    (("fertilizer", "nutrient", "manure", "feed", "substrate", "consumable"), "nutrition_inputs"),
    (("labour",), "labour"),
    (("pesticide", "protection", "medicine", "sanitation", "vaccination", "biosecurity", "treatment"), "protection_and_health"),
    (("maintenance", "repair", "electricity", "utilities", "waste", "breeding"), "utilities_maintenance"),
    (("harvest", "packaging", "grading", "post-harvest", "threshing", "transport", "marketing"), "harvest_marketing"),
    (("staking", "trellis", "pruning", "training", "intercultural", "mulch", "weeding"), "crop_support"),
)


def _scale_factor(land_acres: float) -> float:
    """Economy of scale: larger operations achieve lower per-acre costs.

    Reflects real-world bulk purchasing, equipment amortization, and
    operational efficiency at scale.
    """
    if land_acres < 0.5:
        return 1.25
    if land_acres < 1.0:
        return 1.10
    if land_acres <= 3.0:
        return 1.0
    if land_acres <= 5.0:
        return 0.95
    if land_acres <= 10.0:
        return 0.90
    if land_acres <= 25.0:
        return 0.82
    if land_acres <= 50.0:
        return 0.75
    return 0.70  # 50+ acres — significant bulk/mechanization savings


def _avg_cost(row: dict[str, Any]) -> float:
    return ((row.get("min_inr_per_acre") or 0) + (row.get("max_inr_per_acre") or 0)) / 2


def _component_family(name: str, cost_type: str) -> str:
    text = (name or "").strip().lower()
    for keywords, family in _KEYWORD_FAMILIES:
        if any(keyword in text for keyword in keywords):
            return family
    return "other_capex" if cost_type == "CAPEX" else "other_opex"


def _component_weight(name: str) -> float:
    text = (name or "").lower()
    if "optional" in text:
        return 0.40
    if "recommended" in text:
        return 0.75
    return 1.0


def _capex_floor_weight(family: str, name: str) -> float:
    if family in {"site_preparation", "irrigation_system", "structure"}:
        return 0.95 * _component_weight(name)
    if family in {"support_systems", "tools_equipment", "planting_material"}:
        return 0.85 * _component_weight(name)
    return 0.70 * _component_weight(name)


def _opex_fill_weight(name: str) -> float:
    return 0.85 * _component_weight(name)


def _average_time_to_income_months(crop_info: dict[str, Any] | None) -> float:
    if not crop_info:
        return 3.0
    min_months = crop_info.get("time_to_first_income_months_min", 3) or 3
    max_months = crop_info.get("time_to_first_income_months_max", min_months) or min_months
    return max((min_months + max_months) / 2, 1.0)


def _crop_cycles_per_year(crop_info: dict[str, Any] | None) -> float:
    """Realistic crop cycles per year.

    Short-duration vegetables and pulses can be grown 2-3 times; long-cycle
    crops like sugarcane or orchards yield once. A good consultant accounts
    for realistic turnaround time (gap between harvest and next sowing).
    """
    if not crop_info:
        return 1.0
    avg_duration = _average_time_to_income_months(crop_info)
    category = (crop_info.get("category") or "").upper()
    seasons = (crop_info.get("seasons_supported") or "").upper()

    if avg_duration >= 12 or "ORCHARD" in category or "PERENNIAL" in category or "PLANTATION" in category:
        return 1.0

    # Multi-season crops (KHARIF + RABI or YEAR_ROUND) can practically achieve
    # multiple cycles. Add 0.5 month turnaround between cycles.
    effective_cycle = avg_duration + 0.5
    cycles = 12 / effective_cycle

    # Realistically cap based on season support
    if "YEAR_ROUND" in seasons or ("KHARIF" in seasons and "RABI" in seasons):
        return max(0.8, min(cycles, 3.5))
    if "ZAID" in seasons:
        return max(0.8, min(cycles, 3.0))
    # Single-season crops still get one cycle
    return max(0.8, min(cycles, 2.0))


def _season_start_delay_months(
    planning_month: int | None,
    seasons_supported: str | None,
) -> int:
    if not planning_month or not seasons_supported or not (seasons_supported or "").strip():
        return 0

    supported = {season.strip().upper() for season in (seasons_supported or "").split(",") if season.strip()}
    if not supported or supported.intersection({"ALL", "BOTH", "PERENNIAL"}):
        return 0

    current = "KHARIF" if planning_month in (6, 7, 8, 9, 10) else "RABI"
    if current in supported or ("ZAID" in supported and planning_month in (3, 4, 5)):
        return 0

    delays = []
    for season in supported:
        start_month = _SEASON_START_MONTH.get(season)
        if start_month is None:
            continue
        delay = (start_month - planning_month) % 12
        delays.append(delay if delay > 0 else 12)
    return min(delays) if delays else 0


def _is_long_gestation_crop(crop_info: dict[str, Any] | None) -> bool:
    if not crop_info:
        return False
    category = (crop_info.get("category") or "").upper()
    avg_duration = _average_time_to_income_months(crop_info)
    return (
        avg_duration >= 18
        or "ORCHARD" in category
        or "PERENNIAL" in category
        or "PLANTATION" in category
        or "AGROFORESTRY" in category
    )


def _bearing_fraction(crop_info: dict[str, Any] | None, horizon_months: int) -> float:
    if not crop_info or horizon_months <= 0:
        return 1.0
    category = (crop_info.get("category") or "").upper()
    avg_gestation = _average_time_to_income_months(crop_info)
    if avg_gestation < 12 and "ORCHARD" not in category and "PERENNIAL" not in category:
        return 1.0
    bearing_months = max(horizon_months - avg_gestation, 0)
    return bearing_months / horizon_months


def _risk_cost_delta(
    crop_info: dict[str, Any] | None,
    labour_availability: str,
    water_availability: str,
) -> float:
    if not crop_info:
        return 0.02

    delta = 0.0
    risk_level = (crop_info.get("risk_level") or "MED").upper()
    perishability = (crop_info.get("perishability") or "MED").upper()
    crop_water_need = (crop_info.get("water_need") or "MED").upper()
    crop_labour_need = (crop_info.get("labour_need") or "MED").upper()
    category = (crop_info.get("category") or "").upper()

    delta += {"LOW": 0.00, "MED": 0.02, "MED_HIGH": 0.03, "HIGH": 0.04}.get(risk_level, 0.02)
    delta += {"LOW": 0.00, "MED": 0.01, "MED_HIGH": 0.02, "HIGH": 0.03}.get(perishability, 0.01)

    if water_availability == "LOW":
        delta += {"LOW": 0.00, "MED": 0.01, "HIGH": 0.02}.get(crop_water_need, 0.01)
    if labour_availability == "LOW":
        delta += {"LOW": 0.00, "MED": 0.01, "HIGH": 0.02}.get(crop_labour_need, 0.01)

    if "PROTECTED" in category or "HYDROPONIC" in category:
        delta += 0.02

    return delta


def _scenario_reference(conn: sqlite3.Connection, practice_code: str) -> dict[str, float]:
    row = get_economics_scenario_reference(conn, practice_code) or {}
    return {
        "capital_buffer_floor_months": float(row.get("capital_buffer_floor_months") or _DEFAULT_SCENARIO_REFERENCE["capital_buffer_floor_months"]),
        "capex_contingency_pct": float(row.get("capex_contingency_pct") or _DEFAULT_SCENARIO_REFERENCE["capex_contingency_pct"]),
        "best_case_opex_multiplier": float(row.get("best_case_opex_multiplier") or _DEFAULT_SCENARIO_REFERENCE["best_case_opex_multiplier"]),
        "base_case_opex_multiplier": float(row.get("base_case_opex_multiplier") or _DEFAULT_SCENARIO_REFERENCE["base_case_opex_multiplier"]),
        "worst_case_opex_multiplier": float(row.get("worst_case_opex_multiplier") or _DEFAULT_SCENARIO_REFERENCE["worst_case_opex_multiplier"]),
    }


def _cashflow_projection_months(horizon_months: int) -> int:
    """Projection window for cashflow/break-even analysis.

    For short horizons (1-2 years), extend reasonably to find break-even.
    For longer horizons (5+ years), don't extend much beyond — if break-even
    isn't within 1.5x the horizon, the plan itself needs rethinking.
    Previous: always extended to 120-180 months (10-15 years!) which produced
    unrealistically long break-even times.
    """
    if horizon_months <= 12:
        return max(horizon_months, 36)  # 3 years for annual plans
    if horizon_months <= 36:
        return max(horizon_months, 60)  # 5 years for 2-3 year plans
    # For longer horizons, extend by at most 50%
    return min(int(horizon_months * 1.5), 120)


def _annualized_roi_pct(
    ending_cash_position: float,
    capital_required: float,
    horizon_months: int,
) -> float:
    if capital_required <= 0 or horizon_months <= 0:
        return 0.0

    total_return_multiple = 1 + (ending_cash_position / capital_required)
    if total_return_multiple <= 0:
        return -100.0

    annualized = (total_return_multiple ** (12 / horizon_months)) - 1
    return annualized * 100


def _month_bucket(event_month: float, total_months: int) -> int | None:
    if event_month <= 0 or total_months <= 0:
        return None
    if event_month > total_months + 1e-9:
        return None
    return min(max(int(math.ceil(event_month)) - 1, 0), total_months - 1)


@dataclass
class CropEconomics:
    crop_id: str
    crop_name: str
    area_acres: float
    area_fraction: float
    capex_per_acre: float = 0.0
    opex_per_acre: float = 0.0
    irrigation_capex_per_acre: float = 0.0
    irrigation_opex_per_acre: float = 0.0
    practice_capex_topup_per_acre: float = 0.0
    practice_opex_topup_per_acre: float = 0.0
    physical_capex_per_acre: float = 0.0
    capitalized_working_capital_per_acre: float = 0.0
    capex_contingency_per_acre: float = 0.0
    labour_adjusted_opex_per_acre: float = 0.0
    season_start_delay_months: int = 0
    active_horizon_months: int = 0
    total_setup_capex: float = 0.0
    total_capex: float = 0.0
    total_opex_annual: float = 0.0
    total_opex_horizon: float = 0.0
    revenue_per_acre_annual: float = 0.0
    first_income_months: float = 0.0
    components: list[dict[str, Any]] = field(default_factory=list)
    has_db_data: bool = False
    used_llm_estimate: bool = False


@dataclass
class ScenarioResult:
    scenario: str
    annual_revenue: float = 0.0
    steady_state_annual_revenue: float = 0.0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    profit: float = 0.0
    roi_pct: float = 0.0
    annualized_roi_pct: float = 0.0
    capital_required: float = 0.0
    peak_cash_deficit: float = 0.0
    payback_status: str = "NOT_REACHED"
    breakeven_months: float | None = None


@dataclass
class SensitivityItem:
    factor: str
    description: str
    adjusted_revenue: float = 0.0
    adjusted_cost: float = 0.0
    adjusted_profit: float = 0.0
    adjusted_roi_pct: float = 0.0
    still_profitable: bool = True


@dataclass
class FullEconomics:
    crop_economics: list[CropEconomics]
    scenarios: list[ScenarioResult]
    sensitivities: list[SensitivityItem]
    total_setup_capex: float = 0.0
    total_capex: float = 0.0
    total_annual_opex: float = 0.0
    total_opex_horizon: float = 0.0
    data_coverage: float = 0.0
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _capture_component(
    ce: CropEconomics,
    *,
    component_name: str,
    cost_type: str,
    avg_cost: float,
    min_cost: float = 0.0,
    max_cost: float = 0.0,
    source: str = "kb",
) -> None:
    ce.components.append(
        {
            "component": component_name,
            "component_family": _component_family(component_name, cost_type),
            "cost_type": cost_type,
            "avg_inr_per_acre": round(avg_cost, 0),
            "min_inr_per_acre": round(min_cost, 0),
            "max_inr_per_acre": round(max_cost, 0),
            "source": source,
        }
    )


def _add_missing_practice_costs(
    ce: CropEconomics,
    practice_costs: list[dict[str, Any]],
) -> tuple[float, float]:
    if not practice_costs:
        return 0.0, 0.0

    crop_family_costs: dict[tuple[str, str], float] = defaultdict(float)
    crop_family_seen: set[tuple[str, str]] = set()
    for component in ce.components:
        cost_type = component.get("cost_type", "OPEX")
        family = component.get("component_family") or _component_family(component.get("component", ""), cost_type)
        crop_family_costs[(cost_type, family)] += float(component.get("avg_inr_per_acre", 0) or 0)
        crop_family_seen.add((cost_type, family))

    practice_family_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in practice_costs:
        cost_type = row.get("cost_type", "OPEX")
        family = _component_family(row.get("component", ""), cost_type)
        practice_family_rows[(cost_type, family)].append(row)

    capex_topup = 0.0
    opex_topup = 0.0

    for (cost_type, family), rows in practice_family_rows.items():
        practice_total = sum(_avg_cost(row) * _component_weight(row.get("component", "")) for row in rows)
        if practice_total <= 0:
            continue

        existing_total = crop_family_costs.get((cost_type, family), 0.0)
        if cost_type == "CAPEX":
            target_total = max(_capex_floor_weight(family, rows[0].get("component", "")) * practice_total, existing_total)
            gap = max(target_total - existing_total, 0.0)
            if gap > 0:
                capex_topup += gap
                _capture_component(
                    ce,
                    component_name=f"practice_capex_topup::{family}",
                    cost_type="CAPEX",
                    avg_cost=gap,
                    source="practice_floor",
                )
        elif (cost_type, family) not in crop_family_seen:
            gap = practice_total * _opex_fill_weight(rows[0].get("component", ""))
            if gap > 0:
                opex_topup += gap
                _capture_component(
                    ce,
                    component_name=f"practice_opex_fill::{family}",
                    cost_type="OPEX",
                    avg_cost=gap,
                    source="practice_fill",
                )

    return capex_topup, opex_topup


# ── ICAR fertilizer cost estimation ────────────────────────────────────

# Standard Indian government-rate fertilizer prices (INR per kg of nutrient)
# Source: Nutrient-Based Subsidy (NBS) retail prices, 2024-25 typical rates
_UREA_PRICE_PER_KG_N = 5.36        # Urea ≈ ₹242/45kg bag → ₹5.36/kg N (46% N)
_DAP_PRICE_PER_KG_P2O5 = 29.17     # DAP ≈ ₹1,350/50kg → ~₹29.17/kg P₂O₅ (46% P₂O₅)
_MOP_PRICE_PER_KG_K2O = 16.83      # MOP ≈ ₹840/50kg → ~₹16.83/kg K₂O (60% K₂O)
_FYM_PRICE_PER_TONNE = 800.0       # FYM ~ ₹800/tonne (farm-gate)
_ZINC_SULPHATE_PRICE_PER_KG = 95.0 # ZnSO₄ 21% ~ ₹95/kg


def _load_fertilizer_prices(conn: sqlite3.Connection) -> dict[str, float]:
    """Load fertilizer input prices from DB; fall back to hardcoded constants."""
    mapping = {
        "UREA": _UREA_PRICE_PER_KG_N,
        "DAP": _DAP_PRICE_PER_KG_P2O5,
        "MOP": _MOP_PRICE_PER_KG_K2O,
        "FYM": _FYM_PRICE_PER_TONNE,
        "ZINC_SULPHATE": _ZINC_SULPHATE_PRICE_PER_KG,
    }
    try:
        rows = get_fertilizer_input_costs(conn)
        for row in rows:
            name = row.get("input_name", "")
            price = float(row.get("price_per_unit", 0) or 0)
            if name in mapping and price > 0:
                mapping[name] = price
    except Exception:
        pass  # table may not exist yet; use hardcoded fallback
    return mapping


def _estimate_fertilizer_cost_from_icar(
    conn: sqlite3.Connection,
    crop_id: str,
    state: str | None,
    planning_month: int | None,
) -> float | None:
    """Estimate per-acre fertilizer OPEX from ICAR nutrient plan data.

    Converts NPK kg/ha + FYM t/ha + zinc to product quantities at government
    rates (from DB or hardcoded fallback), then converts from per-hectare to
    per-acre (÷ 2.471).

    Returns total fertilizer cost per acre (INR), or None if no ICAR data.
    """
    if not state:
        return None

    season = detect_season(planning_month) if planning_month else None
    if not season:
        return None

    icar_states = normalize_state_for_icar(state)
    icar_names = match_id_to_icar_names(crop_id)
    if not icar_names:
        return None

    # Load prices from DB (with hardcoded fallback)
    fert_prices = _load_fertilizer_prices(conn)

    for icar_state in icar_states:
        for name in icar_names:
            rows = get_icar_nutrient_plan(conn, icar_state, season, name)
            if not rows:
                continue

            r = rows[0]
            cost_per_ha = 0.0

            n_kg = float(r.get("N_kg_ha") or 0)
            p_kg = float(r.get("P_kg_ha") or 0)
            k_kg = float(r.get("K_kg_ha") or 0)
            fym_t = float(r.get("FYM_t_ha") or 0)
            zinc_kg = float(r.get("zinc_sulphate_kg_ha") or 0)

            cost_per_ha += n_kg * fert_prices["UREA"]
            cost_per_ha += p_kg * fert_prices["DAP"]
            cost_per_ha += k_kg * fert_prices["MOP"]
            cost_per_ha += fym_t * fert_prices["FYM"]
            cost_per_ha += zinc_kg * fert_prices["ZINC_SULPHATE"]

            if cost_per_ha > 0:
                # Convert hectare → acre (1 ha = 2.471 acres)
                return round(cost_per_ha / 2.471, 0)

    return None


def compute_crop_economics(
    conn: sqlite3.Connection,
    crop_id: str,
    crop_name: str,
    area_acres: float,
    area_fraction: float,
    practice_code: str,
    labour_availability: str,
    irrigation_source: str,
    water_availability: str,
    land_total_acres: float,
    horizon_months: int,
    capital_buffer_floor_months: float,
    capex_contingency_pct: float,
    planning_month: int | None = None,
    llm_client: BaseLLMClient | None = None,
    *,
    state: str | None = None,
) -> CropEconomics:
    ce = CropEconomics(
        crop_id=crop_id,
        crop_name=crop_name,
        area_acres=area_acres,
        area_fraction=area_fraction,
    )

    crop_info = get_crop_by_id(conn, crop_id)
    crop_labour_need = (crop_info or {}).get("labour_need", "MED")
    crop_costs = get_crop_costs(conn, crop_id)
    practice_costs = get_practice_costs(conn, practice_code)

    if crop_costs:
        ce.has_db_data = True
        for row in crop_costs:
            avg = _avg_cost(row)
            cost_type = row.get("cost_type", "OPEX")
            component_name = row.get("component", "unknown")
            _capture_component(
                ce,
                component_name=component_name,
                cost_type=cost_type,
                avg_cost=avg,
                min_cost=float(row.get("min_inr_per_acre", 0) or 0),
                max_cost=float(row.get("max_inr_per_acre", 0) or 0),
                source="crop_kb",
            )
            if cost_type == "CAPEX":
                ce.capex_per_acre += avg
            else:
                ce.opex_per_acre += avg
    elif practice_costs:
        for row in practice_costs:
            avg = _avg_cost(row) * _component_weight(row.get("component", ""))
            cost_type = row.get("cost_type", "OPEX")
            _capture_component(
                ce,
                component_name=f"practice_estimate::{row.get('component', 'unknown')}",
                cost_type=cost_type,
                avg_cost=avg,
                source="practice_estimate",
            )
            if cost_type == "CAPEX":
                ce.capex_per_acre += avg
            else:
                ce.opex_per_acre += avg
    else:
        llm_estimate = estimate_crop_costs_with_llm(
            llm_client,
            crop_name=crop_name,
            practice_code=practice_code,
            crop_info=crop_info,
            land_total_acres=land_total_acres,
            irrigation_source=irrigation_source,
            water_availability=water_availability,
            labour_availability=labour_availability,
            horizon_months=horizon_months,
        )
        if llm_estimate:
            ce.capex_per_acre = float(llm_estimate["capex_per_acre"])
            ce.opex_per_acre = float(llm_estimate["annual_opex_per_acre"])
            ce.used_llm_estimate = True
            _capture_component(
                ce,
                component_name="llm_estimated_capex",
                cost_type="CAPEX",
                avg_cost=ce.capex_per_acre,
                source="llm_estimate",
            )
            _capture_component(
                ce,
                component_name="llm_estimated_annual_opex",
                cost_type="OPEX",
                avg_cost=ce.opex_per_acre,
                source="llm_estimate",
            )

    # ── ICAR fertilizer cost supplement ──────────────────────────────
    # If nutrition_inputs family is absent from assembled costs, use ICAR
    # nutrient plan to estimate precise, state-specific fertilizer costs.
    has_nutrition = any(
        c.get("component_family") == "nutrition_inputs"
        for c in ce.components
        if c.get("cost_type") == "OPEX"
    )
    if not has_nutrition and state:
        icar_fert_cost = _estimate_fertilizer_cost_from_icar(
            conn, crop_id, state, planning_month
        )
        if icar_fert_cost and icar_fert_cost > 0:
            _capture_component(
                ce,
                component_name="icar_fertilizer_estimate",
                cost_type="OPEX",
                avg_cost=icar_fert_cost,
                source="icar_nutrient_plan",
            )
            ce.opex_per_acre += icar_fert_cost
            logger.info(
                "ICAR fertilizer cost for %s in %s: ₹%.0f/acre",
                crop_name, state, icar_fert_cost,
            )

    capex_topup, opex_topup = _add_missing_practice_costs(ce, practice_costs)
    ce.practice_capex_topup_per_acre = capex_topup
    ce.practice_opex_topup_per_acre = opex_topup
    ce.capex_per_acre += capex_topup
    ce.opex_per_acre += opex_topup

    labour_mult = _LABOUR_MULTIPLIER.get((labour_availability, crop_labour_need), 1.0)
    # Use per-category labour share from DB; fall back to 0.35
    crop_category = (crop_info or {}).get("category", "").upper() if crop_info else ""
    labour_share = get_crop_labour_share(conn, crop_category) if crop_category else 0.35
    labour_portion = ce.opex_per_acre * labour_share
    non_labour_portion = ce.opex_per_acre * (1.0 - labour_share)
    ce.labour_adjusted_opex_per_acre = (labour_portion * labour_mult) + non_labour_portion

    has_irrigation_component = any(
        component["component_family"] == "irrigation_system"
        for component in ce.components
        if component["cost_type"] == "CAPEX"
    )
    irr_source = irrigation_source or "NONE"
    # Look up irrigation costs from DB; fall back to hardcoded dicts
    irr_db = get_irrigation_costs(conn, irr_source)
    irr_capex = float(irr_db["capex_per_acre"]) if irr_db else _IRRIGATION_CAPEX_PER_ACRE.get(irr_source, 0)
    irr_opex = float(irr_db["opex_per_acre"]) if irr_db else _IRRIGATION_OPEX_PER_ACRE.get(irr_source, 0)
    if not has_irrigation_component:
        ce.irrigation_capex_per_acre = irr_capex
    if not any(
        component["component_family"] == "irrigation_system"
        for component in ce.components
        if component["cost_type"] == "OPEX"
    ):
        ce.irrigation_opex_per_acre = irr_opex * _WATER_OPEX_MULTIPLIER.get(water_availability, 1.0)

    scale = _scale_factor(land_total_acres)
    ce.physical_capex_per_acre = (ce.capex_per_acre + ce.irrigation_capex_per_acre) * scale
    annual_opex_per_acre = (ce.labour_adjusted_opex_per_acre + ce.irrigation_opex_per_acre) * scale

    ce.season_start_delay_months = _season_start_delay_months(
        planning_month,
        (crop_info or {}).get("seasons_supported"),
    )
    ce.active_horizon_months = max(horizon_months - ce.season_start_delay_months, 0)
    ce.first_income_months = _average_time_to_income_months(crop_info)

    # Working capital: only capitalize essential pre-income months, NOT the
    # full buffer floor. For short-cycle crops (<6 months to income), use
    # just first_income_months. Cap at 50% of physical CAPEX to prevent
    # the working capital from dominating the investment figure.
    raw_cap_months = min(
        ce.active_horizon_months,
        max(ce.first_income_months, capital_buffer_floor_months),
    )
    # For annual/seasonal crops, cap capitalization at the crop's own cycle
    category = (crop_info.get("category") or "").upper() if crop_info else ""
    if ce.first_income_months <= 6 and "ORCHARD" not in category and "PERENNIAL" not in category:
        raw_cap_months = min(raw_cap_months, ce.first_income_months + 1)
    raw_wc = annual_opex_per_acre * (raw_cap_months / 12)
    # Cap working capital at 50% of physical CAPEX to keep the investment
    # figure realistic — a consultancy would never show WC > setup cost
    ce.capitalized_working_capital_per_acre = min(raw_wc, ce.physical_capex_per_acre * 0.50)
    ce.capex_contingency_per_acre = ce.physical_capex_per_acre * capex_contingency_pct

    final_capex_per_acre = ce.physical_capex_per_acre + ce.capex_contingency_per_acre + ce.capitalized_working_capital_per_acre
    final_annual_opex_per_acre = annual_opex_per_acre

    _capture_component(
        ce,
        component_name="capex_contingency",
        cost_type="CAPEX",
        avg_cost=ce.capex_contingency_per_acre,
        source="scenario_reference",
    )
    if ce.capitalized_working_capital_per_acre > 0:
        _capture_component(
            ce,
            component_name="pre_income_working_capital",
            cost_type="CAPEX",
            avg_cost=ce.capitalized_working_capital_per_acre,
            source="cashflow_model",
        )

    ce.capex_per_acre = round(final_capex_per_acre, 0)
    ce.opex_per_acre = round(final_annual_opex_per_acre, 0)
    ce.total_setup_capex = round(
        (ce.physical_capex_per_acre + ce.capex_contingency_per_acre) * area_acres,
        0,
    )
    ce.total_capex = round(final_capex_per_acre * area_acres, 0)
    ce.total_opex_annual = round(final_annual_opex_per_acre * area_acres, 0)

    full_horizon_opex = final_annual_opex_per_acre * area_acres * (ce.active_horizon_months / 12)
    ce.total_opex_horizon = round(full_horizon_opex, 0)
    return ce


def _scenario_keys(scenario: str) -> tuple[str, str, str]:
    yield_key_map = {
        "best": "high_yield_per_acre",
        "base": "base_yield_per_acre",
        "worst": "low_yield_per_acre",
    }
    price_key_map = {
        "best": "high_price_per_unit",
        "base": "base_price_per_unit",
        "worst": "low_price_per_unit",
    }
    loss_key_map = {
        "best": "loss_pct_low",
        "base": "loss_pct_base",
        "worst": "loss_pct_high",
    }
    return yield_key_map[scenario], price_key_map[scenario], loss_key_map[scenario]


def _budget_yield_boost(budget_per_acre: float, scenario: str) -> float:
    """When budget per acre is generous, farmers use better inputs (hybrid seeds,
    adequate fertilizer, timely pest control) leading to higher realized yields.

    A consultancy would model this as "input intensity → yield response".
    Returns a multiplier 1.0–1.15 for base, 1.0–1.10 for best, 1.0–1.05 for worst.
    """
    # Budget thresholds (INR/acre): below 30k = basic, 30-80k = moderate, 80k+ = intensive
    if budget_per_acre <= 30_000:
        return 1.0
    if budget_per_acre <= 80_000:
        intensity = (budget_per_acre - 30_000) / 50_000  # 0 to 1
    else:
        intensity = 1.0

    boost_cap = {"best": 0.10, "base": 0.15, "worst": 0.05}
    return 1.0 + intensity * boost_cap.get(scenario, 0.10)


def _scenario_crop_revenue_profile(
    conn: sqlite3.Connection,
    crop_id: str,
    *,
    area_acres: float,
    scenario: str,
    projection_months: int,
    planning_month: int | None = None,
    budget_per_acre: float = 0.0,
    override_yield_bands: dict | None = None,
) -> tuple[list[float], float]:
    revenue = [0.0] * projection_months
    if area_acres <= 0 or projection_months <= 0:
        return revenue, 0.0

    yield_key, price_key, loss_key = _scenario_keys(scenario)
    # Use state-specific yield bands if provided; else fall back to national
    yield_data = override_yield_bands or get_yield_bands(conn, crop_id)
    price_data = get_price_bands(conn, crop_id)
    crop_info = get_crop_by_id(conn, crop_id)
    if not yield_data or not price_data:
        logger.warning("Missing yield/price data for %s", crop_id)
        return revenue, 0.0

    perishability = (crop_info or {}).get("perishability", "MED")
    loss_data = get_loss_factor(conn, perishability)
    yield_val = float(yield_data.get(yield_key, 0) or 0)
    # Budget-aware yield boost: higher investment → better inputs → better yield
    yield_boost = _budget_yield_boost(budget_per_acre, scenario)
    yield_val *= yield_boost
    price_val = float(price_data.get(price_key, 0) or 0)
    loss_pct = float((loss_data or {}).get(loss_key, 10) or 10) / 100
    # Higher budget also reduces post-harvest loss (better storage/handling)
    if budget_per_acre > 50_000:
        loss_reduction = min(0.30, (budget_per_acre - 50_000) / 200_000)  # up to 30% loss reduction
        loss_pct *= (1 - loss_reduction)
    marketable_revenue_per_harvest = yield_val * price_val * (1 - loss_pct) * area_acres

    season_delay = _season_start_delay_months(planning_month, (crop_info or {}).get("seasons_supported"))
    first_income = _average_time_to_income_months(crop_info)

    if _is_long_gestation_crop(crop_info):
        steady_state_annual_revenue = marketable_revenue_per_harvest
        event_month = season_delay + first_income
        harvest_number = 0
        while True:
            bucket = _month_bucket(event_month, projection_months)
            if bucket is None:
                break
            tree_ramp = _get_tree_ramp(crop_id)
            ramp = tree_ramp[min(harvest_number, len(tree_ramp) - 1)]
            revenue[bucket] += marketable_revenue_per_harvest * ramp
            event_month += 12
            harvest_number += 1
        return revenue, steady_state_annual_revenue

    cycles_per_year = _crop_cycles_per_year(crop_info)
    cycle_months = max(12 / cycles_per_year, 1.0)
    steady_state_annual_revenue = marketable_revenue_per_harvest * cycles_per_year
    event_month = season_delay + first_income
    while True:
        bucket = _month_bucket(event_month, projection_months)
        if bucket is None:
            break
        revenue[bucket] += marketable_revenue_per_harvest
        event_month += cycle_months
    return revenue, steady_state_annual_revenue


def compute_scenario_revenue(
    conn: sqlite3.Connection,
    portfolio: list[dict[str, Any]],
    land_acres: float,
    scenario: str,
    horizon_months: int = 12,
    planning_month: int | None = None,
) -> float:
    total_revenue = 0.0
    horizon_years = max(horizon_months / 12, 1 / 12)

    for entry in portfolio:
        area = land_acres * entry["area_fraction"]
        revenue_profile, _ = _scenario_crop_revenue_profile(
            conn,
            entry["crop_id"],
            area_acres=area,
            scenario=scenario,
            projection_months=horizon_months,
            planning_month=planning_month,
        )
        total_revenue += sum(revenue_profile[:horizon_months])

    return total_revenue / horizon_years


def _portfolio_risk_delta(
    conn: sqlite3.Connection,
    portfolio_entries: list[dict[str, Any]],
    labour_availability: str,
    water_availability: str,
) -> float:
    if not portfolio_entries:
        return 0.0
    weighted = 0.0
    for entry in portfolio_entries:
        crop_info = get_crop_by_id(conn, entry["crop_id"])
        weighted += _risk_cost_delta(crop_info, labour_availability, water_availability) * entry["area_fraction"]
    return weighted


def _scenario_cost_multiplier(
    scenario_reference: dict[str, float],
    scenario: str,
    risk_delta: float,
) -> float:
    base = {
        "best": scenario_reference["best_case_opex_multiplier"],
        "base": scenario_reference["base_case_opex_multiplier"],
        "worst": scenario_reference["worst_case_opex_multiplier"],
    }[scenario]
    risk_weight = {"best": 0.15, "base": 0.35, "worst": 1.0}[scenario]
    return max(0.90, base + (risk_delta * risk_weight))


def _build_scenario_cashflow(
    conn: sqlite3.Connection,
    *,
    crop_economics: dict[str, CropEconomics],
    portfolio_entries: list[dict[str, Any]],
    land_acres: float,
    scenario: str,
    cost_multiplier: float,
    projection_months: int,
    planning_month: int | None = None,
    budget_per_acre: float = 0.0,
) -> tuple[list[float], float]:
    monthly_net = [0.0] * projection_months
    steady_state_annual_revenue = 0.0

    for entry in portfolio_entries:
        ce = crop_economics.get(entry["crop_id"])
        if ce is None:
            continue

        area = land_acres * entry["area_fraction"]
        revenue_profile, steady_revenue = _scenario_crop_revenue_profile(
            conn,
            entry["crop_id"],
            area_acres=area,
            scenario=scenario,
            projection_months=projection_months,
            planning_month=planning_month,
            budget_per_acre=budget_per_acre,
        )
        steady_state_annual_revenue += steady_revenue

        if monthly_net:
            monthly_net[0] -= ce.total_setup_capex

        monthly_opex = (ce.total_opex_annual * cost_multiplier) / 12
        for month_idx in range(ce.season_start_delay_months, projection_months):
            monthly_net[month_idx] -= monthly_opex

        for month_idx, revenue in enumerate(revenue_profile):
            monthly_net[month_idx] += revenue

    return monthly_net, steady_state_annual_revenue


def compute_full_economics(
    conn: sqlite3.Connection,
    portfolio_entries: list[dict[str, Any]],
    practice_code: str,
    land_acres: float,
    horizon_months: int,
    labour_availability: str,
    irrigation_source: str,
    water_availability: str,
    budget_total_inr: int,
    planning_month: int | None = None,
    llm_client: BaseLLMClient | None = None,
    *,
    state: str | None = None,
) -> FullEconomics:
    horizon_years = max(horizon_months / 12, 1)
    projection_months = _cashflow_projection_months(horizon_months)
    scenario_reference = _scenario_reference(conn, practice_code)

    result = FullEconomics(
        crop_economics=[],
        scenarios=[],
        sensitivities=[],
        assumptions=[],
        warnings=[],
    )

    crops_with_data = 0
    for entry in portfolio_entries:
        area = land_acres * entry["area_fraction"]
        ce = compute_crop_economics(
            conn=conn,
            crop_id=entry["crop_id"],
            crop_name=entry["crop_name"],
            area_acres=area,
            area_fraction=entry["area_fraction"],
            practice_code=practice_code,
            labour_availability=labour_availability,
            irrigation_source=irrigation_source,
            water_availability=water_availability,
            land_total_acres=land_acres,
            horizon_months=horizon_months,
            planning_month=planning_month,
            capital_buffer_floor_months=scenario_reference["capital_buffer_floor_months"],
            capex_contingency_pct=scenario_reference["capex_contingency_pct"],
            llm_client=llm_client,
            state=state,
        )
        if ce.has_db_data:
            crops_with_data += 1
        result.crop_economics.append(ce)

    crop_economics_by_id = {ce.crop_id: ce for ce in result.crop_economics}

    # ── CAPEX budget cap ──────────────────────────────────────────────
    # The budget is the farmer's available capital.  If modelled CAPEX
    # exceeds it, we scale down all cost components proportionally so
    # the plan stays fundable.  This mirrors what a consultancy does:
    # "design to budget", not "warn and overshoot".
    raw_total_capex = sum(ce.total_capex for ce in result.crop_economics)
    capex_was_capped = False
    if budget_total_inr > 0 and raw_total_capex > budget_total_inr:
        capex_was_capped = True
        budget_scale = budget_total_inr / raw_total_capex
        for ce in result.crop_economics:
            ce.physical_capex_per_acre = round(ce.physical_capex_per_acre * budget_scale, 0)
            ce.capex_contingency_per_acre = round(ce.capex_contingency_per_acre * budget_scale, 0)
            ce.capitalized_working_capital_per_acre = round(
                ce.capitalized_working_capital_per_acre * budget_scale, 0
            )
            ce.capex_per_acre = round(
                ce.physical_capex_per_acre
                + ce.capex_contingency_per_acre
                + ce.capitalized_working_capital_per_acre,
                0,
            )
            area = land_acres * ce.area_fraction
            ce.total_setup_capex = round(
                (ce.physical_capex_per_acre + ce.capex_contingency_per_acre) * area, 0
            )
            ce.total_capex = round(ce.capex_per_acre * area, 0)

    result.total_setup_capex = sum(ce.total_setup_capex for ce in result.crop_economics)
    result.total_capex = sum(ce.total_capex for ce in result.crop_economics)
    result.total_annual_opex = sum(ce.total_opex_annual for ce in result.crop_economics)
    result.total_opex_horizon = sum(ce.total_opex_horizon for ce in result.crop_economics)
    result.data_coverage = crops_with_data / len(portfolio_entries) if portfolio_entries else 0

    risk_delta = _portfolio_risk_delta(conn, portfolio_entries, labour_availability, water_availability)
    budget_per_acre = budget_total_inr / land_acres if land_acres > 0 else 0.0

    for scenario in ("best", "base", "worst"):
        cost_multiplier = _scenario_cost_multiplier(scenario_reference, scenario, risk_delta)
        monthly_net, steady_state_annual_revenue = _build_scenario_cashflow(
            conn=conn,
            crop_economics=crop_economics_by_id,
            portfolio_entries=portfolio_entries,
            land_acres=land_acres,
            scenario=scenario,
            cost_multiplier=cost_multiplier,
            projection_months=projection_months,
            planning_month=planning_month,
            budget_per_acre=budget_per_acre,
        )
        annual_opex = result.total_annual_opex * cost_multiplier
        total_opex = result.total_opex_horizon * cost_multiplier
        total_cost = result.total_setup_capex + total_opex

        cumulative = 0.0
        min_cumulative = 0.0
        breakeven = None
        for month_idx, month_net in enumerate(monthly_net, start=1):
            cumulative += month_net
            min_cumulative = min(min_cumulative, cumulative)
            if breakeven is None and cumulative >= 0:
                breakeven = round(float(month_idx), 1)

        total_revenue = round(sum(month for month in monthly_net[:horizon_months]) + total_cost, 0)
        annual_revenue = total_revenue / horizon_years if horizon_years > 0 else 0.0
        profit = round(sum(month for month in monthly_net[:horizon_months]), 0)
        peak_cash_deficit = abs(min_cumulative)
        capital_required = max(result.total_capex, peak_cash_deficit)
        roi_pct = (profit / total_cost * 100) if total_cost > 0 else 0.0
        annualized_roi = _annualized_roi_pct(profit, total_cost, horizon_months)

        if breakeven is not None:
            payback_status = "WITHIN_HORIZON" if breakeven <= horizon_months else "BEYOND_HORIZON"
        else:
            trailing_window = monthly_net[max(0, projection_months - 12):]
            payback_status = "NOT_PROFITABLE" if sum(trailing_window) <= 0 else "NOT_REACHED"

        result.scenarios.append(
            ScenarioResult(
                scenario=scenario,
                annual_revenue=round(annual_revenue, 0),
                steady_state_annual_revenue=round(steady_state_annual_revenue, 0),
                total_revenue=round(total_revenue, 0),
                total_cost=round(total_cost, 0),
                profit=round(profit, 0),
                roi_pct=round(roi_pct, 1),
                annualized_roi_pct=round(annualized_roi, 1),
                capital_required=round(capital_required, 0),
                peak_cash_deficit=round(peak_cash_deficit, 0),
                payback_status=payback_status,
                breakeven_months=breakeven,
            )
        )

    base_scenario = next((scenario for scenario in result.scenarios if scenario.scenario == "base"), None)
    if base_scenario and base_scenario.total_revenue > 0:
        base_rev = base_scenario.total_revenue
        base_cost = base_scenario.total_cost

        sensitivity_configs = [
            ("price_-15%", "Farmgate price drops 15%", 0.85, 1.0),
            ("price_-25%", "Farmgate price drops 25%", 0.75, 1.0),
            ("yield_-10%", "Yield drops 10% due to weather or pest stress", 0.90, 1.0),
            ("yield_-20%", "Yield drops 20% in a bad production season", 0.80, 1.0),
            ("labour_+10%", "Labour costs increase 10%", 1.0, 1.10),
            ("labour_+20%", "Labour costs increase 20%", 1.0, 1.20),
            ("input_+15%", "Input costs increase 15%", 1.0, 1.15),
        ]

        for factor, description, revenue_multiplier, cost_multiplier in sensitivity_configs:
            adjusted_revenue = base_rev * revenue_multiplier
            adjusted_cost = result.total_setup_capex + (base_cost - result.total_setup_capex) * cost_multiplier
            adjusted_profit = adjusted_revenue - adjusted_cost
            adjusted_roi = (adjusted_profit / adjusted_cost * 100) if adjusted_cost > 0 else 0
            result.sensitivities.append(
                SensitivityItem(
                    factor=factor,
                    description=description,
                    adjusted_revenue=round(adjusted_revenue, 0),
                    adjusted_cost=round(adjusted_cost, 0),
                    adjusted_profit=round(adjusted_profit, 0),
                    adjusted_roi_pct=round(adjusted_roi, 1),
                    still_profitable=adjusted_profit > 0,
                )
            )

    result.assumptions = _build_assumptions(
        land_acres=land_acres,
        horizon_months=horizon_months,
        labour=labour_availability,
        irrigation=irrigation_source,
        water=water_availability,
        practice=practice_code,
        scenario_reference=scenario_reference,
        econ=result,
        budget_per_acre=budget_per_acre,
        capex_was_capped=capex_was_capped,
        raw_total_capex=raw_total_capex,
        budget_total_inr=budget_total_inr,
    )
    result.warnings = _build_warnings(
        econ=result,
        budget=budget_total_inr,
        land=land_acres,
        horizon=horizon_months,
    )
    return result


def _build_assumptions(
    *,
    land_acres: float,
    horizon_months: int,
    labour: str,
    irrigation: str,
    water: str,
    practice: str,
    scenario_reference: dict[str, float],
    econ: FullEconomics,
    budget_per_acre: float = 0.0,
    capex_was_capped: bool = False,
    raw_total_capex: float = 0.0,
    budget_total_inr: int = 0,
) -> list[str]:
    assumptions = [
        f"Land area: {land_acres} acres",
        f"Planning horizon: {horizon_months} months ({horizon_months / 12:.1f} years)",
        f"Labour availability: {labour}",
        f"Irrigation source: {irrigation}",
        f"Water availability: {water}",
        f"Farming practice: {practice}",
        "Crop-level CAPEX/OPEX is blended with practice-level cost profiles to fill missing setup and operating components",
        f"CAPEX includes setup contingency ({scenario_reference['capex_contingency_pct'] * 100:.0f}%) and a pre-income working-capital reserve for capital planning",
        f"Minimum pre-income capital buffer from scenario reference: {scenario_reference['capital_buffer_floor_months']:.1f} months",
        "Best/base/worst revenue uses crop yield bands, price bands, post-harvest loss bands, gestation timing, and crop-cycle harvest events",
        "Best/base/worst cost uses practice-specific OPEX multipliers with additional crop risk, perishability, labour, and water stress adjustments",
        "ROI is measured against the larger of modeled peak cash deficit and total capital requirement so working capital is not double-counted as an expense",
        "Annual revenue figures represent horizon-average realization; steady-state annual revenue is kept separately for long-gestation crops",
        "Small plots (<1 acre) carry higher per-acre overhead; larger farms (10+ acres) receive significant scale efficiency (bulk inputs, mechanization)",
    ]
    if capex_was_capped and raw_total_capex > 0 and budget_total_inr > 0:
        reduction_pct = (1 - budget_total_inr / raw_total_capex) * 100
        assumptions.append(
            f"CAPEX was capped to fit the stated budget (₹{budget_total_inr:,.0f}). "
            f"Modelled full-specification cost was ₹{raw_total_capex:,.0f} — "
            f"investment intensity reduced by {reduction_pct:.0f}% to stay within budget. "
            "Input quality, contingency reserves, or working capital may be lower than ideal."
        )
    if budget_per_acre > 50_000:
        boost = _budget_yield_boost(budget_per_acre, "base")
        assumptions.append(
            f"Higher investment intensity (₹{budget_per_acre:,.0f}/acre) enables better inputs → "
            f"yield uplift of {(boost - 1) * 100:.0f}% over baseline, with reduced post-harvest losses"
        )
    season_delays = [crop for crop in econ.crop_economics if crop.season_start_delay_months > 0]
    if season_delays:
        delay_summary = ", ".join(
            f"{crop.crop_name} (+{crop.season_start_delay_months}mo)"
            for crop in season_delays
        )
        assumptions.append(
            "Season support affects first revenue timing for crops that miss the stated planning month: "
            + delay_summary
        )
    if any(crop.used_llm_estimate for crop in econ.crop_economics):
        assumptions.append("LLM cost estimates were used only for crops with no structured crop or practice cost rows")
    return assumptions


def _build_warnings(
    *,
    econ: FullEconomics,
    budget: int,
    land: float,
    horizon: int,
) -> list[str]:
    warnings: list[str] = []

    # Budget overshoot warning is no longer needed — CAPEX is now capped
    # at the user's budget in compute_full_economics().  We keep a
    # softer note if the raw (pre-cap) model would have been higher.
    if budget > 0 and econ.total_capex >= budget * 0.95:
        warnings.append(
            f"Investment plan has been fitted to the stated budget ({_fmt(budget)}). "
            "Input intensity or contingency may be lower than ideal — consider increasing "
            "the budget if possible for better yields and risk coverage."
        )

    if budget > 0 and econ.total_capex + econ.total_annual_opex > budget:
        warnings.append(
            "Initial investment plus one full operating year exceeds the stated budget. "
            "Working capital or phased deployment may be required."
        )

    base = next((scenario for scenario in econ.scenarios if scenario.scenario == "base"), None)
    worst = next((scenario for scenario in econ.scenarios if scenario.scenario == "worst"), None)

    if base and budget > 0 and base.capital_required > budget:
        warnings.append(
            f"Base-case peak funding need ({_fmt(base.capital_required)}) is above the stated budget "
            f"({_fmt(budget)}). Extra working capital or phased rollout may be needed."
        )

    if base and base.roi_pct < 0:
        warnings.append("Base scenario shows negative ROI. Review crop mix, area, or investment intensity.")
    if worst and worst.profit < 0:
        warnings.append("Worst-case scenario results in a loss. Plan for price, yield, and working-capital shocks.")
    if base and base.payback_status == "BEYOND_HORIZON" and base.breakeven_months:
        warnings.append(
            f"Break-even ({base.breakeven_months:.0f} months) exceeds the planning horizon "
            f"({horizon} months). Returns may not be realized within the selected window."
        )
    if base and base.payback_status == "NOT_PROFITABLE":
        warnings.append(
            "Modeled cashflows do not turn positive within the extended projection window. "
            "This plan may not recover invested capital under current assumptions."
        )
    if econ.data_coverage < 0.5:
        warnings.append(
            f"Only {econ.data_coverage * 100:.0f}% of crops have detailed crop-level cost data. "
            "Practice-level fills or fallback estimates may influence accuracy."
        )

    llm_crops = [crop.crop_name for crop in econ.crop_economics if crop.used_llm_estimate]
    if llm_crops:
        warnings.append(
            "Structured cost data was missing for: "
            + ", ".join(sorted(llm_crops))
            + ". LLM-based cost estimation was used for those crops."
        )

    unprofitable_sensitivities = [item for item in econ.sensitivities if not item.still_profitable]
    if len(unprofitable_sensitivities) >= 3:
        warnings.append(
            f"{len(unprofitable_sensitivities)} out of {len(econ.sensitivities)} sensitivity scenarios turn loss-making. "
            "This plan has limited financial resilience."
        )

    season_delays = [crop for crop in econ.crop_economics if crop.season_start_delay_months > 0]
    if season_delays:
        warnings.append(
            "Some crops do not align cleanly with the selected planning month, which delays first revenue: "
            + ", ".join(
                f"{crop.crop_name} (+{crop.season_start_delay_months} months)"
                for crop in season_delays
            )
        )

    if land < 1:
        warnings.append("Very small land parcels carry higher per-acre establishment cost and tighter margins.")

    return warnings


def build_graph_payload(econ: FullEconomics) -> dict[str, Any]:
    return {
        "roi_chart": [
            {
                "scenario": scenario.scenario.capitalize(),
                "scenario_key": scenario.scenario,
                "revenue": scenario.total_revenue,
                "cost": scenario.total_cost,
                "profit": scenario.profit,
                "roi_pct": scenario.roi_pct,
                "annualized_roi_pct": scenario.annualized_roi_pct,
                "capital_required": scenario.capital_required,
            }
            for scenario in econ.scenarios
        ],
        "cost_chart": [
            {
                "crop_name": crop.crop_name,
                "capex": crop.capex_per_acre,
                "opex": crop.opex_per_acre,
                "total": crop.capex_per_acre + crop.opex_per_acre,
            }
            for crop in econ.crop_economics
        ],
        "sensitivity_chart": [
            {
                "factor": item.factor.replace("_", " "),
                "adjusted_roi": item.adjusted_roi_pct,
                "still_profitable": item.still_profitable,
            }
            for item in econ.sensitivities
        ],
        "breakeven_chart": [
            {
                "scenario": scenario.scenario.capitalize(),
                "months": scenario.breakeven_months or 0,
                "status": scenario.payback_status,
            }
            for scenario in econ.scenarios
            if scenario.breakeven_months is not None
        ],
        "cost_composition": _cost_composition_chart(econ),
    }


def _cost_composition_chart(econ: FullEconomics) -> list[dict[str, Any]]:
    total = econ.total_capex + econ.total_opex_horizon
    if total <= 0:
        return []
    return [
        {"name": "CAPEX", "value": econ.total_capex, "pct": round(econ.total_capex / total * 100, 1)},
        {"name": "OPEX (horizon)", "value": econ.total_opex_horizon, "pct": round(econ.total_opex_horizon / total * 100, 1)},
    ]


def build_ui_payload(econ: FullEconomics) -> dict[str, Any]:
    base = next((scenario for scenario in econ.scenarios if scenario.scenario == "base"), None)
    best = next((scenario for scenario in econ.scenarios if scenario.scenario == "best"), None)
    worst = next((scenario for scenario in econ.scenarios if scenario.scenario == "worst"), None)

    cards = [
        {"label": "Total CAPEX", "value": econ.total_capex, "unit": "INR", "color": "indigo"},
        {"label": "Setup CAPEX", "value": econ.total_setup_capex, "unit": "INR", "color": "indigo"},
        {"label": "Annual OPEX", "value": econ.total_annual_opex, "unit": "INR", "color": "violet"},
        {"label": "Total OPEX (Horizon)", "value": econ.total_opex_horizon, "unit": "INR", "color": "purple"},
    ]

    if base:
        cards.extend(
            [
                {"label": "Est. Revenue (Base)", "value": base.total_revenue, "unit": "INR", "color": "green"},
                {
                    "label": "Est. Profit (Base)",
                    "value": base.profit,
                    "unit": "INR",
                    "color": "green" if base.profit >= 0 else "red",
                },
                {
                    "label": "ROI (Base)",
                    "value": base.roi_pct,
                    "unit": "%",
                    "color": "green" if base.roi_pct >= 0 else "red",
                },
                {
                    "label": "Annualized ROI",
                    "value": base.annualized_roi_pct,
                    "unit": "%",
                    "color": "green" if base.annualized_roi_pct >= 0 else "red",
                },
                {
                    "label": "Peak Funding Gap",
                    "value": base.capital_required,
                    "unit": "INR",
                    "color": "blue",
                },
                {"label": "Break-even", "value": base.breakeven_months, "unit": "months", "color": "blue"},
            ]
        )
    if best:
        cards.append({"label": "Best-case Profit", "value": best.profit, "unit": "INR", "color": "emerald"})
    if worst:
        cards.append(
            {
                "label": "Worst-case Profit",
                "value": worst.profit,
                "unit": "INR",
                "color": "emerald" if worst.profit >= 0 else "red",
            }
        )

    return {
        "summary_cards": cards,
        "assumptions": econ.assumptions,
        "warnings": econ.warnings,
        "data_coverage_pct": round(econ.data_coverage * 100, 0),
    }


def _fmt(n: float) -> str:
    return f"\u20B9{n:,.0f}"
