from growgrid_core.agents.step_9_field_layout_agent import _generate_expert_tips
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import FieldBlock, ValidatedProfile


def _profile() -> ValidatedProfile:
    return ValidatedProfile(
        location="Maharashtra, Pune",
        land_area_acres=2.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=300_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=2.0,
        risk_tolerance=RiskLevel.MED,
        budget_per_acre=150_000.0,
        horizon_months=24,
    )


def test_generate_expert_tips_handles_vegetable_crop_ids() -> None:
    blocks = [
        FieldBlock(
            crop_id="VE_TOMATO",
            crop_name="Tomato",
            area_acres=1.0,
            block_label="A",
        )
    ]

    tips = _generate_expert_tips(blocks, _profile(), "OPEN_FIELD_VEG")

    assert any("yellow sticky traps" in tip for tip in tips)
