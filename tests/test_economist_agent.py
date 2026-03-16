from __future__ import annotations

from growgrid_core.agents.economist_calculations import (
    compute_crop_economics,
    compute_full_economics,
)
from growgrid_core.agents.step_7_economist_agent import EconomistAgent
from growgrid_core.tools.llm_client import MockLLMClient
from growgrid_core.tools.tavily_client import MockTavilyClient
from growgrid_core.utils.enums import Goal, IrrigationSource, LabourLevel, RiskLevel, WaterLevel
from growgrid_core.utils.types import (
    AgronomistVerification,
    CropPortfolioEntry,
    EconomistOutput,
    PlanRequest,
    PracticeScore,
    ValidatedProfile,
)


def _seed_loss_factor(conn) -> None:
    conn.execute(
        """INSERT INTO loss_factor_reference (
            perishability_level, loss_pct_low, loss_pct_base, loss_pct_high, notes
        ) VALUES (?, ?, ?, ?, ?)""",
        ("HIGH", 5, 10, 18, "test"),
    )
    conn.execute(
        """INSERT INTO loss_factor_reference (
            perishability_level, loss_pct_low, loss_pct_base, loss_pct_high, notes
        ) VALUES (?, ?, ?, ?, ?)""",
        ("LOW", 1, 3, 5, "test"),
    )


def _seed_open_field_economics(
    conn,
    *,
    crop_id: str,
    yield_rows: tuple[float, float, float],
    price_rows: tuple[float, float, float],
) -> None:
    conn.executemany(
        """INSERT INTO crop_cost_profile (
            crop_id, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (crop_id, "seed_or_planting_material", "CAPEX", 2500, 4500, ""),
            (crop_id, "fertilizer_and_nutrients", "OPEX", 3500, 6500, ""),
            (crop_id, "labour", "OPEX", 4000, 7000, ""),
        ],
    )
    conn.execute("DELETE FROM practice_cost_profile WHERE practice_code = 'OPEN_FIELD'")
    conn.executemany(
        """INSERT INTO practice_cost_profile (
            practice_code, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("OPEN_FIELD", "Land Preparation", "CAPEX", 2000, 6000, ""),
            ("OPEN_FIELD", "Harvest + Packaging", "OPEX", 1500, 5000, ""),
        ],
    )
    conn.execute("DELETE FROM economics_scenario_reference WHERE practice_code = 'OPEN_FIELD'")
    conn.execute(
        """INSERT INTO economics_scenario_reference (
            practice_code, capital_buffer_floor_months, capex_contingency_pct,
            best_case_opex_multiplier, base_case_opex_multiplier, worst_case_opex_multiplier, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("OPEN_FIELD", 3, 0.05, 0.98, 1.0, 1.12, "test"),
    )
    conn.execute(
        """INSERT INTO yield_baseline_bands (
            crop_id, low_yield_per_acre, base_yield_per_acre, high_yield_per_acre, yield_unit, source_notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        (crop_id, yield_rows[0], yield_rows[1], yield_rows[2], "quintal_per_acre", "test"),
    )
    conn.execute(
        """INSERT INTO price_baseline_bands (
            crop_id, low_price_per_unit, base_price_per_unit, high_price_per_unit, price_unit, source_notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        (crop_id, price_rows[0], price_rows[1], price_rows[2], "INR_per_quintal", "test"),
    )


def test_practice_cost_completion_and_working_capital_raise_capex(test_db):
    conn = test_db
    conn.executemany(
        """INSERT INTO crop_cost_profile (
            crop_id, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("TOMATO", "seed_or_planting_material", "CAPEX", 3000, 6000, ""),
            ("TOMATO", "fertilizer_and_nutrients", "OPEX", 4000, 7000, ""),
            ("TOMATO", "labour", "OPEX", 7000, 12000, ""),
            ("TOMATO", "pesticide_and_protection", "OPEX", 3000, 6000, ""),
        ],
    )
    conn.executemany(
        """INSERT INTO practice_cost_profile (
            practice_code, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("OPEN_FIELD", "Land Preparation", "CAPEX", 4000, 8000, ""),
            ("OPEN_FIELD", "Irrigation Setup", "CAPEX", 5000, 15000, ""),
            ("OPEN_FIELD", "Harvest + Packaging", "OPEX", 3000, 9000, ""),
            ("OPEN_FIELD", "Transport / Marketing", "OPEX", 2000, 7000, ""),
        ],
    )
    conn.execute(
        """INSERT INTO economics_scenario_reference (
            practice_code, capital_buffer_floor_months, capex_contingency_pct,
            best_case_opex_multiplier, base_case_opex_multiplier, worst_case_opex_multiplier, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("OPEN_FIELD", 4, 0.06, 0.98, 1.0, 1.12, "test"),
    )
    conn.commit()

    ce = compute_crop_economics(
        conn=conn,
        crop_id="TOMATO",
        crop_name="Tomato",
        area_acres=1.0,
        area_fraction=1.0,
        practice_code="OPEN_FIELD",
        labour_availability="MED",
        irrigation_source="BOREWELL",
        water_availability="MED",
        land_total_acres=1.0,
        horizon_months=12,
        capital_buffer_floor_months=4,
        capex_contingency_pct=0.06,
    )

    assert ce.capex_per_acre > 25_000
    assert ce.capex_per_acre > 4_500
    assert ce.total_opex_horizon == ce.total_opex_annual
    assert any(c["component"] == "pre_income_working_capital" for c in ce.components)
    assert any(c["component"].startswith("practice_capex_topup::") for c in ce.components)


def test_scenario_costs_and_roi_are_ordered_using_reference_and_risk(test_db):
    conn = test_db
    conn.executemany(
        """INSERT INTO crop_cost_profile (
            crop_id, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("MANGO", "seed_or_planting_material", "CAPEX", 12000, 18000, ""),
            ("MANGO", "fertilizer_and_nutrients", "OPEX", 5000, 8000, ""),
            ("MANGO", "labour", "OPEX", 7000, 12000, ""),
            ("MANGO", "pesticide_and_protection", "OPEX", 2000, 5000, ""),
        ],
    )
    conn.executemany(
        """INSERT INTO practice_cost_profile (
            practice_code, component, cost_type, min_inr_per_acre, max_inr_per_acre, notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("ORCHARD", "Pit Digging & Planting", "CAPEX", 10000, 22000, ""),
            ("ORCHARD", "Drip Irrigation", "CAPEX", 12000, 25000, ""),
            ("ORCHARD", "Pruning Tools", "CAPEX", 2000, 6000, ""),
            ("ORCHARD", "Harvesting & Packaging", "OPEX", 5000, 15000, ""),
        ],
    )
    conn.execute(
        """INSERT INTO economics_scenario_reference (
            practice_code, capital_buffer_floor_months, capex_contingency_pct,
            best_case_opex_multiplier, base_case_opex_multiplier, worst_case_opex_multiplier, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("ORCHARD", 12, 0.08, 0.97, 1.0, 1.16, "test"),
    )
    conn.execute(
        """INSERT INTO yield_baseline_bands (
            crop_id, low_yield_per_acre, base_yield_per_acre, high_yield_per_acre, yield_unit, source_notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        ("MANGO", 20, 35, 50, "quintal_per_acre", "test"),
    )
    conn.execute(
        """INSERT INTO price_baseline_bands (
            crop_id, low_price_per_unit, base_price_per_unit, high_price_per_unit, price_unit, source_notes
        ) VALUES (?, ?, ?, ?, ?, ?)""",
        ("MANGO", 1200, 1800, 2600, "INR_per_quintal", "test"),
    )
    _seed_loss_factor(conn)
    conn.commit()

    econ = compute_full_economics(
        conn=conn,
        portfolio_entries=[{"crop_id": "MANGO", "crop_name": "Mango", "area_fraction": 1.0}],
        practice_code="ORCHARD",
        land_acres=1.0,
        horizon_months=60,
        labour_availability="MED",
        irrigation_source="BOREWELL",
        water_availability="MED",
        budget_total_inr=500_000,
    )

    best = next(item for item in econ.scenarios if item.scenario == "best")
    base = next(item for item in econ.scenarios if item.scenario == "base")
    worst = next(item for item in econ.scenarios if item.scenario == "worst")

    assert best.total_revenue > base.total_revenue > worst.total_revenue
    assert best.total_cost < base.total_cost < worst.total_cost
    assert best.roi_pct > base.roi_pct > worst.roi_pct
    assert base.breakeven_months is None or base.breakeven_months >= 48
    assert base.payback_status in {"NOT_REACHED", "BEYOND_HORIZON", "NOT_PROFITABLE"}
    assert base.capital_required >= econ.total_setup_capex
    assert "Best/base/worst cost uses practice-specific OPEX multipliers" in " ".join(econ.assumptions)


def test_llm_fallback_used_when_no_cost_rows_exist(test_db):
    conn = test_db
    llm = MockLLMClient(
        responses=[
            {
                "capex_per_acre": 40_000,
                "annual_opex_per_acre": 24_000,
                "rationale": "Estimated from open-field vegetable establishment and annual inputs.",
            }
        ]
    )

    ce = compute_crop_economics(
        conn=conn,
        crop_id="ONION",
        crop_name="Onion",
        area_acres=1.0,
        area_fraction=1.0,
        practice_code="OPEN_FIELD",
        labour_availability="MED",
        irrigation_source="BOREWELL",
        water_availability="MED",
        land_total_acres=1.0,
        horizon_months=12,
        capital_buffer_floor_months=3,
        capex_contingency_pct=0.05,
        llm_client=llm,
    )

    assert ce.used_llm_estimate is True
    assert ce.capex_per_acre > 40_000
    assert any(component["source"] == "llm_estimate" for component in ce.components)


def test_planning_month_delay_reduces_realized_revenue(test_db):
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn,
        crop_id="MILLET",
        yield_rows=(5, 8, 12),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    immediate = compute_full_economics(
        conn=conn,
        portfolio_entries=[{"crop_id": "MILLET", "crop_name": "Pearl Millet (Bajra)", "area_fraction": 1.0}],
        practice_code="OPEN_FIELD",
        land_acres=1.0,
        horizon_months=12,
        labour_availability="LOW",
        irrigation_source="NONE",
        water_availability="LOW",
        budget_total_inr=80_000,
        planning_month=7,
    )
    delayed = compute_full_economics(
        conn=conn,
        portfolio_entries=[{"crop_id": "MILLET", "crop_name": "Pearl Millet (Bajra)", "area_fraction": 1.0}],
        practice_code="OPEN_FIELD",
        land_acres=1.0,
        horizon_months=12,
        labour_availability="LOW",
        irrigation_source="NONE",
        water_availability="LOW",
        budget_total_inr=80_000,
        planning_month=1,
    )

    base_immediate = next(item for item in immediate.scenarios if item.scenario == "base")
    base_delayed = next(item for item in delayed.scenarios if item.scenario == "base")

    assert base_immediate.total_revenue > base_delayed.total_revenue
    assert base_immediate.breakeven_months is not None
    assert base_delayed.breakeven_months is None or base_delayed.breakeven_months > base_immediate.breakeven_months
    assert any("delays first revenue" in warning for warning in delayed.warnings)


def test_economist_agent_prefers_agronomist_verified_portfolio(test_db):
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn,
        crop_id="TOMATO",
        yield_rows=(150, 220, 300),
        price_rows=(600, 900, 1300),
    )
    _seed_open_field_economics(
        conn,
        crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    profile = ValidatedProfile(
        location="Maharashtra, Pune",
        land_area_acres=1.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=150_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=1.0,
        risk_tolerance=RiskLevel.MED,
        budget_per_acre=150_000,
        horizon_months=12,
        planning_month=11,
    )
    request = PlanRequest(
        location="Maharashtra, Pune",
        land_area_acres=1.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=150_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=1.0,
        risk_tolerance=RiskLevel.MED,
        planning_month=11,
    )
    state = {
        "validated_profile": profile,
        "selected_practice": PracticeScore(
            practice_code="OPEN_FIELD",
            practice_name="Open Field Farming",
            fit_scores={"water": 1, "labour": 1, "risk": 1, "time": 1, "profit": 1, "capex": 1},
            weighted_score=1.0,
        ),
        "selected_crop_portfolio": [
            CropPortfolioEntry(
                crop_id="TOMATO",
                crop_name="Tomato",
                area_fraction=1.0,
                role_hint="PRIMARY",
                score=0.95,
            )
        ],
        "agronomist_verification": AgronomistVerification(
            verified_crop_portfolio=[
                CropPortfolioEntry(
                    crop_id="WHEAT",
                    crop_name="Wheat",
                    area_fraction=1.0,
                    role_hint="PRIMARY",
                    score=0.85,
                )
            ]
        ),
    }

    result = EconomistAgent(conn=conn).run(state, request)

    assert result["economics"].cost_breakdown[0].crop_id == "WHEAT"


def _make_agent_state(conn, *, crop_id="WHEAT", crop_name="Wheat"):
    """Helper to create a minimal agent state for economist tests."""
    profile = ValidatedProfile(
        location="Maharashtra, Pune",
        land_area_acres=2.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=200_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=1.0,
        risk_tolerance=RiskLevel.MED,
        budget_per_acre=100_000,
        horizon_months=12,
        planning_month=11,
    )
    request = PlanRequest(
        location="Maharashtra, Pune",
        land_area_acres=2.0,
        water_availability=WaterLevel.MED,
        irrigation_source=IrrigationSource.BOREWELL,
        budget_total_inr=200_000,
        labour_availability=LabourLevel.MED,
        goal=Goal.MAXIMIZE_PROFIT,
        time_horizon_years=1.0,
        risk_tolerance=RiskLevel.MED,
        planning_month=11,
    )
    state = {
        "validated_profile": profile,
        "selected_practice": PracticeScore(
            practice_code="OPEN_FIELD",
            practice_name="Open Field Farming",
            fit_scores={"water": 1, "labour": 1, "risk": 1, "time": 1, "profit": 1, "capex": 1},
            weighted_score=1.0,
        ),
        "selected_crop_portfolio": [
            CropPortfolioEntry(
                crop_id=crop_id,
                crop_name=crop_name,
                area_fraction=1.0,
                role_hint="PRIMARY",
                score=0.90,
            )
        ],
    }
    return state, request


def test_economist_v2_produces_three_scenarios(test_db):
    """New economist agent outputs conservative/base/optimistic scenarios."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(conn=conn).run(state, request)

    economist_output: EconomistOutput = result["economist_output"]
    assert "conservative" in economist_output.scenarios
    assert "base" in economist_output.scenarios
    assert "optimistic" in economist_output.scenarios

    # Optimistic should be better than conservative
    opt = economist_output.scenarios["optimistic"]
    con = economist_output.scenarios["conservative"]
    assert opt.total_revenue >= con.total_revenue
    assert opt.roi_percent >= con.roi_percent


def test_economist_v2_monthly_cashflow_has_12_months(test_db):
    """Monthly cashflow should have exactly 12 entries."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(conn=conn).run(state, request)

    cashflow = result["economist_output"].monthly_cashflow_year1
    assert len(cashflow) == 12
    assert cashflow[0].month == 1
    assert cashflow[11].month == 12

    # First month should have the largest expense (includes setup)
    assert cashflow[0].operating_expense >= cashflow[1].operating_expense


def test_economist_v2_sensitivity_analysis(test_db):
    """Sensitivity analysis should have 5 shocks."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(conn=conn).run(state, request)

    sensitivity = result["economist_output"].sensitivity_analysis
    assert len(sensitivity) == 5
    factors = {s.factor for s in sensitivity}
    assert "price_drop_20%" in factors
    assert "yield_drop_20%" in factors


def test_economist_v2_data_quality_without_tavily(test_db):
    """Without Tavily, data quality should reflect DB-only sourcing."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(conn=conn).run(state, request)

    dq = result["economist_output"].data_quality_summary
    assert dq is not None
    assert dq.overall_quality in {"HIGH", "MED", "LOW"}
    # Without Tavily, no live prices
    assert len(dq.fields_from_live_fetch) == 0


def test_economist_v2_backward_compat_economics_report(test_db):
    """Backward-compatible EconomicsReport is still produced."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(conn=conn).run(state, request)

    economics = result["economics"]
    assert len(economics.cost_breakdown) > 0
    assert len(economics.roi_summary) == 3
    assert economics.total_capex > 0
    assert economics.data_coverage > 0


def test_economist_v2_with_mock_tavily(test_db):
    """With Tavily providing live prices, data quality reflects it."""
    conn = test_db
    _seed_loss_factor(conn)
    _seed_open_field_economics(
        conn, crop_id="WHEAT",
        yield_rows=(10, 16, 22),
        price_rows=(1800, 2200, 2600),
    )
    conn.commit()

    tavily = MockTavilyClient(
        results=[
            {
                "title": "Wheat Price Maharashtra",
                "url": "https://example.com",
                "content": "Wheat 2000-2400 INR/quintal",
            }
        ]
    )
    llm = MockLLMClient(
        responses=[
            {
                "price_min": 2000,
                "price_max": 2400,
                "source": "example.com",
                "confidence": "HIGH",
            }
        ]
    )

    state, request = _make_agent_state(conn, crop_id="WHEAT", crop_name="Wheat")
    result = EconomistAgent(
        conn=conn,
        llm_client=llm,
        tavily_client=tavily,
    ).run(state, request)

    output = result["economist_output"]
    # Live prices should be reflected in price sources
    assert len(output.price_sources) > 0
    assert output.price_sources[0].source == "live_fetch"
    assert output.price_sources[0].confidence == "HIGH"
