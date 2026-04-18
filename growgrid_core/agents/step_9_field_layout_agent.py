"""Agent 9 — Field Layout Planner Agent.

Converts crop portfolio + area split into a practical, implementable spatial
layout that mirrors advice an experienced farmer / crop planning expert
would give:
    - precise spacing plan per crop (from crop_spacing_reference DB table)
    - plant/tree count per block with exact field dimensions
    - planting pattern, depth, bed type, and irrigation method
    - companion planting suggestions and border crop advice
    - pathway and irrigation layout planning
    - expert tips for each block and the overall field

Fully deterministic — no LLM calls.
Falls back to category-based default spacing when DB data is missing.
"""

from __future__ import annotations

import logging
import math
import sqlite3
from typing import Any

from growgrid_core.agents.base_agent import BaseAgent
from growgrid_core.db.db_loader import load_all
from growgrid_core.db.queries import (
    get_all_spacings_for_crop,
    get_crop_by_id,
    get_crop_spacing,
    get_icar_crop_calendar,
)
from growgrid_core.utils.icar_matching import match_id_to_icar_names, normalize_state_for_icar
from growgrid_core.utils.location import parse_state_from_location
from growgrid_core.utils.season import detect_season
from growgrid_core.utils.types import (
    CropPortfolioEntry,
    FieldBlock,
    FieldLayoutPlan,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)

# Broadcast seed rates (kg/acre) for crops sown continuously without plant spacing
_BROADCAST_SEED_RATES: dict[str, float] = {
    "CE_WHEAT": 40.0,
    "CE_RICE": 30.0,
    "CE_MAIZE": 8.0,
    "MI_BAJRA": 2.0,
    "MI_JOWAR": 5.0,
    "MI_RAGI": 4.0,
    "FO_NAPIER": 15000.0,  # slips per acre, not kg
    "DEFAULT_CEREAL": 40.0,
    "DEFAULT_MILLET": 4.0,
    "DEFAULT_FODDER": 40.0,
}

# Category-based default spacings (row_cm, plant_cm, plants_per_acre)
_DEFAULT_SPACING: dict[str, tuple[float, float, int]] = {
    "CEREAL": (22, 0, 800000),
    "MILLET": (45, 15, 23760),
    "PULSE": (30, 10, 53820),
    "OILSEED": (45, 10, 35700),
    "VEGETABLE": (60, 45, 5940),
    "SPICE": (45, 20, 17820),
    "FRUIT_ORCHARD": (600, 600, 45),
    "FRUIT_FIELD": (200, 200, 400),
    "COMMERCIAL": (90, 45, 3960),
    "PROTECTED_VEG": (90, 40, 4460),
    "PROTECTED_FLOWER": (90, 40, 4460),
    "FLOWER": (40, 30, 13380),
    "FODDER": (30, 0, 500000),
    "PLANTATION": (300, 300, 180),
}

# Default planting patterns and bed types by category
_CATEGORY_DEFAULTS: dict[str, dict[str, str]] = {
    "CEREAL": {"pattern": "line_sowing", "bed": "flat", "depth": "4", "irrigation": "flood / sprinkler"},
    "MILLET": {"pattern": "line_sowing", "bed": "flat", "depth": "3", "irrigation": "rainfed / sprinkler"},
    "PULSE": {"pattern": "line_sowing", "bed": "flat", "depth": "4", "irrigation": "rainfed / sprinkler"},
    "OILSEED": {"pattern": "line_sowing", "bed": "flat", "depth": "3", "irrigation": "rainfed / sprinkler"},
    "VEGETABLE": {"pattern": "transplant", "bed": "raised_bed", "depth": "2", "irrigation": "drip / furrow"},
    "SPICE": {"pattern": "line_sowing", "bed": "raised_bed", "depth": "3", "irrigation": "drip / furrow"},
    "FRUIT_ORCHARD": {"pattern": "square_planting", "bed": "pit", "depth": "50", "irrigation": "drip / basin"},
    "FRUIT_FIELD": {"pattern": "square_planting", "bed": "pit", "depth": "30", "irrigation": "drip / basin"},
    "COMMERCIAL": {"pattern": "line_sowing", "bed": "ridge", "depth": "5", "irrigation": "furrow / drip"},
    "PROTECTED_VEG": {"pattern": "transplant", "bed": "raised_bed", "depth": "0", "irrigation": "drip"},
    "PROTECTED_FLOWER": {"pattern": "transplant", "bed": "raised_bed", "depth": "0", "irrigation": "drip"},
    "FLOWER": {"pattern": "transplant", "bed": "raised_bed", "depth": "0", "irrigation": "drip / sprinkler"},
    "FODDER": {"pattern": "line_sowing", "bed": "flat", "depth": "3", "irrigation": "flood / rainfed"},
    "PLANTATION": {"pattern": "square_planting", "bed": "pit", "depth": "45", "irrigation": "drip / basin"},
}

# Companion planting knowledge — maps crop categories to beneficial companions
_COMPANION_MAP: dict[str, list[str]] = {
    "CEREAL": ["Pulses (nitrogen fixation)", "Mustard (pest trap crop)"],
    "MILLET": ["Pulses (intercrop)", "Pigeon pea (boundary)"],
    "PULSE": ["Cereals (mutual benefit)", "Marigold (nematode control)"],
    "OILSEED": ["Chickpea (rabi intercrop)", "Marigold (pest deterrent)"],
    "VEGETABLE": ["Marigold (pest repellent)", "Basil (improves flavour & repels pests)"],
    "SPICE": ["Legumes (soil nitrogen)", "Drumstick (partial shade)"],
    "FRUIT_ORCHARD": ["Legume cover crop (soil health)", "Cowpea/Moong (intercrop in young orchards)"],
    "FRUIT_FIELD": ["Cowpea (ground cover)", "Short-duration vegetables (intercrop)"],
    "COMMERCIAL": ["Moong/Cowpea (rotation crop)", "Marigold (trap crop for bollworm)"],
    "PROTECTED_VEG": ["Basil (companion in polyhouse)", "Marigold (edge planting)"],
    "PROTECTED_FLOWER": ["Herbs (edge companion)", "Neem extract sprays (IPM)"],
    "FLOWER": ["Vegetables (intercrop for income)", "Basil (pest repellent)"],
    "FODDER": ["Pulse intercrop", "Legume mix for soil health"],
    "PLANTATION": ["Pepper vine (intercrop on trees)", "Banana (shade filler in young plantation)"],
}

# Expert planting tips by crop category
_PLANTING_TIPS: dict[str, str] = {
    "CEREAL": "Sow seeds in uniform rows using a seed drill for even germination; ensure soil moisture at sowing",
    "MILLET": "Thin seedlings to proper spacing 15-20 days after sowing; millets tolerate poor soil but respond well to FYM",
    "PULSE": "Treat seeds with Rhizobium culture before sowing for better nitrogen fixation and 10-15% yield boost",
    "OILSEED": "Ensure proper thinning after germination to maintain recommended plant-to-plant spacing",
    "VEGETABLE": "Prepare raised beds 15-20 cm high for better drainage; apply well-decomposed FYM 2 weeks before transplanting",
    "SPICE": "Use disease-free seed rhizomes/planting material; apply thick mulch to conserve moisture and suppress weeds",
    "FRUIT_ORCHARD": "Dig pits 1m x 1m x 1m at least 15-20 days before planting; mix topsoil with 20 kg FYM + 500g SSP per pit",
    "FRUIT_FIELD": "Prepare pits 60cm x 60cm x 60cm; use tissue culture plants for uniformity; stake young plants",
    "COMMERCIAL": "Follow recommended sett/seed treatment; maintain proper earthing up schedule for ridge-planted crops",
    "PROTECTED_VEG": "Ensure drip lines are laid before transplanting; maintain 80-85% humidity in initial establishment phase",
    "PROTECTED_FLOWER": "Sterilize growing media before planting; maintain strict hygiene protocols in polyhouse",
    "FLOWER": "Pinch growing tips at 30 days for bushy growth and more flower heads per plant",
    "FODDER": "Can broadcast or line-sow; first cut at 45-50 days for maximum green fodder yield",
    "PLANTATION": "Plant during onset of monsoon; provide shade for first 2-3 years using temporary shade structures",
}

# Border crop suggestions based on water/wind conditions
_BORDER_CROPS: dict[str, str] = {
    "LOW": "Agave or Sisal (drought-hardy live fence, doubles as fiber crop)",
    "MED": "Moringa or Drumstick (windbreak + nutritious harvest)",
    "HIGH": "Sesbania or Gliricidia (nitrogen-fixing windbreak, can be lopped for green manure)",
}

# 1 acre = 43560 sq ft ≈ 4047 sq m
_SQM_PER_ACRE = 4047.0


def _get_icar_spacing(
    conn: sqlite3.Connection,
    entry: "CropPortfolioEntry",
    profile: "ValidatedProfile",
) -> dict | None:
    """Try to get row/plant spacing from ICAR crop calendar for the farmer's state.

    Returns dict with row_spacing_cm, plant_spacing_cm, plants_per_acre, state
    or None if no ICAR data available.
    """
    state_name = parse_state_from_location(profile.location)
    if not state_name:
        return None

    season = detect_season(profile.planning_month) if profile.planning_month else None
    if not season:
        return None

    icar_states = normalize_state_for_icar(state_name)
    icar_names = match_id_to_icar_names(entry.crop_id)
    if not icar_names:
        icar_names = [entry.crop_name.lower()]

    for icar_state in icar_states:
        for name in icar_names:
            rows = get_icar_crop_calendar(conn, icar_state, season, name)
            for r in rows:
                row_cm = r.get("row_spacing_cm")
                plant_cm = r.get("plant_spacing_cm")
                if row_cm and plant_cm and row_cm > 0 and plant_cm > 0:
                    # Calculate plants per acre
                    plants_per_sqm = 10000 / (row_cm * plant_cm)
                    plants_per_acre = int(plants_per_sqm * _SQM_PER_ACRE)
                    return {
                        "row_spacing_cm": float(row_cm),
                        "plant_spacing_cm": float(plant_cm),
                        "plants_per_acre": plants_per_acre,
                        "state": icar_state,
                    }
    return None


def _get_bed_type(planting_pattern: str, category: str) -> str:
    """Infer bed type from planting pattern and crop category."""
    pattern_bed_map = {
        "ridge_planting": "ridge",
        "raised_bed": "raised_bed",
        "transplant": "raised_bed" if category in ("VEGETABLE", "PROTECTED_VEG", "PROTECTED_FLOWER", "FLOWER") else "flat",
        "rhizome_planting": "raised_bed",
        "sett_planting": "furrow",
        "pillar_planting": "pit_with_pillar",
        "trellis_row": "pit_with_trellis",
        "hedge_row": "pit",
        "indoor_rack": "indoor_rack",
    }
    if planting_pattern in pattern_bed_map:
        return pattern_bed_map[planting_pattern]
    cat_defaults = _CATEGORY_DEFAULTS.get(category, {})
    return cat_defaults.get("bed", "flat")


def _get_irrigation_method(category: str, water_availability: str, practice_code: str) -> str:
    """Recommend irrigation method based on crop type and water situation."""
    if "POLYHOUSE" in practice_code or "PROTECTED" in category:
        return "Drip irrigation (inline drippers at 30-40 cm interval)"
    if category in ("FRUIT_ORCHARD", "PLANTATION"):
        if water_availability == "LOW":
            return "Drip irrigation (4-8 LPH emitters per tree, 2 emitters for young trees)"
        return "Drip irrigation preferred; basin irrigation as fallback"
    if category in ("CEREAL", "FODDER"):
        if water_availability == "HIGH":
            return "Flood irrigation in check basins or border strips"
        return "Sprinkler irrigation (saves 30-40% water vs flood)"
    if category in ("VEGETABLE", "SPICE", "FLOWER"):
        return "Drip irrigation on raised beds (saves 40-50% water, reduces disease)"
    cat_defaults = _CATEGORY_DEFAULTS.get(category, {})
    return cat_defaults.get("irrigation", "As per local practice")


def _generate_expert_tips(
    blocks: list[FieldBlock],
    profile: ValidatedProfile,
    practice_code: str,
) -> list[str]:
    """Generate practical expert tips based on the overall layout."""
    tips: list[str] = []
    land = profile.land_area_acres

    # Field orientation
    tips.append(
        "Orient rows North-South wherever possible — this ensures both sides of the "
        "row get equal sunlight through the day, improving yield by 5-10%."
    )

    # Pathway advice
    if len(blocks) > 1:
        tips.append(
            "Maintain 1.5-2 m wide pathways between blocks for bullock cart / tractor access, "
            "spraying operations, and harvest movement."
        )

    # Irrigation infrastructure
    water = profile.water_availability.value if hasattr(profile.water_availability, 'value') else str(profile.water_availability)
    if water == "LOW":
        tips.append(
            "With limited water, prioritize drip irrigation and mulching. "
            "Apply 5-7 cm paddy straw or black plastic mulch to reduce evaporation by 30-40%."
        )
    elif water == "MED":
        tips.append(
            "Install a drip mainline along the central pathway with sub-mains branching into each block. "
            "This setup is the most efficient for mixed crop layouts."
        )

    # Soil health
    tips.append(
        "Apply 2-3 tonnes of well-decomposed FYM or vermicompost per acre before sowing/planting. "
        "Get a soil test done to calibrate fertilizer doses — it costs very little and saves money on inputs."
    )

    # Pest management
    has_vegetables = any((b.crop_id or "").startswith("VE_") for b in blocks)
    if has_vegetables:
        tips.append(
            "Install yellow sticky traps (8-10 per acre) and pheromone traps for whitefly and fruit borer. "
            "Plant marigold on block borders as a trap crop for nematodes and bollworm."
        )

    # Rotation advice
    if land >= 2:
        tips.append(
            "Plan crop rotation across seasons — follow a cereal/millet with a pulse to restore soil nitrogen, "
            "then a cash crop. This breaks pest cycles and maintains soil fertility."
        )

    # Small farm specific
    if land < 1:
        tips.append(
            "For your plot size, focus on high-value crops with staggered planting for continuous harvest. "
            "Consider selling directly to local consumers or restaurants for better margins."
        )

    # Labour planning
    labour = profile.labour_availability.value if hasattr(profile.labour_availability, 'value') else str(profile.labour_availability)
    if labour == "LOW":
        tips.append(
            "With limited labour, prefer direct-sown crops over transplanted ones. "
            "Use herbicides judiciously for weed management, or apply thick mulch to suppress weeds."
        )

    return tips


class FieldLayoutAgent(BaseAgent):
    """Generate expert-level field layout plan from crop portfolio.

    Produces a practical, implementable layout with precise dimensions,
    planting instructions, companion crops, and expert tips — like advice
    from an experienced crop planning consultant.
    """

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]

        land = profile.land_area_acres
        water = profile.water_availability.value if hasattr(profile.water_availability, 'value') else str(profile.water_availability)
        blocks: list[FieldBlock] = []
        notes: list[str] = []

        for idx, entry in enumerate(portfolio):
            area = land * entry.area_fraction
            block_label = chr(65 + idx)  # A, B, C, ...

            # ── 4-tier spacing lookup ──
            spacing = get_crop_spacing(conn, entry.crop_id, practice.practice_code)
            spacing_source = "reference"
            if not spacing:
                all_spacings = get_all_spacings_for_crop(conn, entry.crop_id)
                spacing = all_spacings[0] if all_spacings else None

            # Get crop info for category
            crop_info = get_crop_by_id(conn, entry.crop_id)
            category = crop_info.get("category", "VEGETABLE") if crop_info else "VEGETABLE"

            if spacing:
                row_cm = spacing.get("row_spacing_cm") or 60
                plant_cm = spacing.get("plant_spacing_cm") or 0
                plants_per_acre = spacing.get("plants_per_acre") or 0
                planting_pattern = spacing.get("planting_pattern") or ""
                depth_cm = spacing.get("depth_cm") or 0
                spacing_notes = spacing.get("notes") or ""
                spacing_source = "reference"
            else:
                # Tier 3: Try ICAR crop calendar for state-specific spacing
                icar_spacing = _get_icar_spacing(conn, entry, profile)
                if icar_spacing:
                    row_cm = icar_spacing["row_spacing_cm"]
                    plant_cm = icar_spacing["plant_spacing_cm"]
                    plants_per_acre = icar_spacing["plants_per_acre"]
                    cat_defs = _CATEGORY_DEFAULTS.get(category, {})
                    planting_pattern = cat_defs.get("pattern", "line_sowing")
                    depth_cm = float(cat_defs.get("depth", "3"))
                    spacing_notes = ""
                    spacing_source = "icar"
                    notes.append(
                        f"Block {block_label} ({entry.crop_name}): spacing from ICAR "
                        f"advisory for {icar_spacing.get('state', 'your state')}."
                    )
                else:
                    # Tier 4: Fallback to category defaults
                    defaults = _DEFAULT_SPACING.get(category, (60, 45, 5940))
                    row_cm, plant_cm, plants_per_acre = defaults
                    cat_defs = _CATEGORY_DEFAULTS.get(category, {})
                    planting_pattern = cat_defs.get("pattern", "line_sowing")
                    depth_cm = float(cat_defs.get("depth", "3"))
                    spacing_notes = ""
                    spacing_source = "default"
                    notes.append(
                        f"Block {block_label} ({entry.crop_name}): using default spacing for "
                        f"{category} category — verify with local KVK or agriculture officer."
                    )

            # ── Detect broadcast crops (plant_spacing_cm == 0) ──
            is_broadcast = plant_cm == 0
            seed_rate_kg = 0.0
            if is_broadcast:
                seed_rate_kg = _BROADCAST_SEED_RATES.get(
                    entry.crop_id,
                    _BROADCAST_SEED_RATES.get(f"DEFAULT_{category}", 40.0),
                )

            # ── Compute field dimensions with variable aspect ratio ──
            area_sqm = area * _SQM_PER_ACRE

            if row_cm > 0 and area > 0:
                row_spacing_m = row_cm / 100

                # Variable aspect ratio: derive from spacing geometry
                if plant_cm > 0:
                    natural_ratio = row_cm / plant_cm
                    ratio = max(1.0, min(3.0, natural_ratio))
                else:
                    ratio = 2.0  # broadcast crops: long narrow for seed drill

                field_length_m = round(math.sqrt(area_sqm * ratio), 1)
                field_width_m = round(area_sqm / field_length_m, 1) if field_length_m > 0 else 0

                # ── Headland deduction for accurate plant counts ──
                headland_m = 2.0 if land >= 1.0 else 1.0
                usable_length = max(field_length_m - 2 * headland_m, 1.0)
                usable_width = max(field_width_m - 2 * headland_m, 1.0)

                total_rows = max(1, int(usable_width / row_spacing_m))
                if is_broadcast:
                    # For broadcast crops, plant count is not meaningful
                    total_plants = int(plants_per_acre * area)
                    plants_per_row = 0
                else:
                    plant_spacing_m = plant_cm / 100
                    plants_per_row = max(1, int(usable_length / plant_spacing_m)) if plant_spacing_m > 0 else 0
                    total_plants = total_rows * plants_per_row
            else:
                field_length_m = round(math.sqrt(area_sqm), 1) if area_sqm > 0 else 0
                field_width_m = field_length_m
                total_rows = 0
                plants_per_row = 0
                total_plants = int(plants_per_acre * area)
                headland_m = 0.0

            # Determine bed type
            bed_type = _get_bed_type(planting_pattern, category)

            # Irrigation method
            irrigation_method = _get_irrigation_method(category, water, practice.practice_code)

            # Companion crops
            companions = _COMPANION_MAP.get(category, [])

            # Planting tip
            planting_tip = _PLANTING_TIPS.get(category, "Follow local best practices for this crop.")

            # Seed rate hint
            if is_broadcast:
                seed_rate_hint = f"Broadcast/line sow at {seed_rate_kg:.0f} kg/acre"
            else:
                seed_rate_hint = spacing_notes if spacing_notes else ""

            blocks.append(FieldBlock(
                crop_id=entry.crop_id,
                crop_name=entry.crop_name,
                area_acres=round(area, 2),
                row_spacing_cm=row_cm,
                plant_spacing_cm=plant_cm,
                total_plants=total_plants,
                rows=total_rows,
                plants_per_row=plants_per_row,
                block_label=f"Block {block_label}",
                planting_pattern=planting_pattern,
                planting_depth_cm=depth_cm,
                field_length_m=field_length_m,
                field_width_m=field_width_m,
                bed_type=bed_type,
                seed_rate_hint=seed_rate_hint,
                irrigation_method=irrigation_method,
                companion_crops=companions,
                planting_tip=planting_tip,
                is_broadcast=is_broadcast,
                seed_rate_kg_per_acre=seed_rate_kg,
                headland_m=headland_m,
                spacing_source=spacing_source,
            ))

        # Overall field notes
        if len(blocks) > 1:
            notes.append("Leave 1.5-2 m pathway between blocks for tractor/cart access and spraying operations.")
            notes.append(
                "Place taller crops (e.g. sugarcane, maize, fruit trees) on the western side "
                "to avoid shading shorter crops."
            )

        # Border crop suggestion
        border_crop = _BORDER_CROPS.get(water, _BORDER_CROPS["MED"])

        # Irrigation layout
        if len(blocks) <= 2:
            irrigation_layout = (
                "Run main water line along the longer edge of the field. "
                "Branch sub-lines into each block perpendicular to crop rows."
            )
        else:
            irrigation_layout = (
                "Install a central main pipeline running through the middle of the field. "
                "Branch sub-mains into each block. Use valves at each junction for block-wise irrigation control. "
                "This allows you to irrigate different crops on different schedules."
            )

        # Generate expert tips
        expert_tips = _generate_expert_tips(blocks, profile, practice.practice_code)

        layout = FieldLayoutPlan(
            blocks=blocks,
            total_area_used_acres=round(sum(b.area_acres for b in blocks), 2),
            notes=notes,
            field_orientation="North-South row orientation recommended for maximum sunlight interception",
            pathway_width_m=1.5 if land < 2 else 2.0,
            border_crop=border_crop,
            irrigation_layout=irrigation_layout,
            expert_tips=expert_tips,
        )

        state["field_layout"] = layout
        logger.info("FieldLayoutAgent: %d blocks planned across %.2f acres.", len(blocks), layout.total_area_used_acres)
        return state
