"""Agent 9 — Field Layout Planner Agent.

Converts crop portfolio + area split into a spatial layout:
    - spacing plan per crop (from crop_spacing_reference DB table)
    - plant/tree count per block
    - block-level layout with labels
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
from growgrid_core.db.queries import get_all_spacings_for_crop, get_crop_by_id, get_crop_spacing
from growgrid_core.utils.types import (
    CropPortfolioEntry,
    FieldBlock,
    FieldLayoutPlan,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
)

logger = logging.getLogger(__name__)

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

# 1 acre = 43560 sq ft ≈ 4047 sq m
_SQM_PER_ACRE = 4047.0


class FieldLayoutAgent(BaseAgent):
    """Generate field layout plan from crop portfolio."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self._conn = conn

    def run(self, state: dict[str, Any], request: PlanRequest) -> dict[str, Any]:
        conn = self._conn or load_all()
        profile: ValidatedProfile = state["validated_profile"]
        practice: PracticeScore = state["selected_practice"]
        portfolio: list[CropPortfolioEntry] = state["selected_crop_portfolio"]

        land = profile.land_area_acres
        blocks: list[FieldBlock] = []
        notes: list[str] = []

        for idx, entry in enumerate(portfolio):
            area = land * entry.area_fraction
            block_label = chr(65 + idx)  # A, B, C, ...

            # Try exact practice match first, then any practice, then category default
            spacing = get_crop_spacing(conn, entry.crop_id, practice.practice_code)
            if not spacing:
                all_spacings = get_all_spacings_for_crop(conn, entry.crop_id)
                spacing = all_spacings[0] if all_spacings else None

            if spacing:
                row_cm = spacing.get("row_spacing_cm") or 60
                plant_cm = spacing.get("plant_spacing_cm") or 0
                plants_per_acre = spacing.get("plants_per_acre") or 0
            else:
                # Fallback to category defaults
                crop_info = get_crop_by_id(conn, entry.crop_id)
                category = crop_info.get("category", "VEGETABLE") if crop_info else "VEGETABLE"
                defaults = _DEFAULT_SPACING.get(category, (60, 45, 5940))
                row_cm, plant_cm, plants_per_acre = defaults
                notes.append(f"Block {block_label} ({entry.crop_name}): using default spacing for {category} category.")

            # Compute plant count and rows
            total_plants = int(plants_per_acre * area)

            if row_cm > 0 and area > 0:
                area_sqm = area * _SQM_PER_ACRE
                row_spacing_m = row_cm / 100
                field_width_m = math.sqrt(area_sqm)
                total_rows = max(1, int(field_width_m / row_spacing_m))
                plants_per_row = max(1, int(total_plants / total_rows)) if total_rows > 0 else total_plants
            else:
                total_rows = 0
                plants_per_row = 0

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
            ))

        if len(blocks) > 1:
            notes.append("Leave 1-2m pathway between blocks for access and operations.")

        layout = FieldLayoutPlan(
            blocks=blocks,
            total_area_used_acres=round(sum(b.area_acres for b in blocks), 2),
            notes=notes,
        )

        state["field_layout"] = layout
        logger.info("FieldLayoutAgent: %d blocks planned across %.2f acres.", len(blocks), layout.total_area_used_acres)
        return state
