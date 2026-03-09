"""Unit tests for growgrid_core.utils.scoring."""

from __future__ import annotations

import math

from growgrid_core.utils.scoring import (
    capex_fit,
    normalize_weights,
    ordinal_fit,
    profit_fit,
    risk_fit,
    time_fit,
    weighted_sum,
)


class TestOrdinalFit:
    def test_perfect_match(self):
        assert ordinal_fit("LOW", "LOW") == 1.0
        assert ordinal_fit("MED", "MED") == 1.0
        assert ordinal_fit("HIGH", "HIGH") == 1.0

    def test_one_step(self):
        assert ordinal_fit("LOW", "MED") == 0.6
        assert ordinal_fit("MED", "HIGH") == 0.6
        assert ordinal_fit("HIGH", "MED") == 0.6

    def test_opposite(self):
        assert ordinal_fit("LOW", "HIGH") == 0.2
        assert ordinal_fit("HIGH", "LOW") == 0.2


class TestCapexFit:
    def test_budget_above_max(self):
        assert capex_fit(100_000, 20_000, 50_000) == 1.0

    def test_budget_below_min(self):
        assert capex_fit(5_000, 20_000, 50_000) == 0.0

    def test_budget_at_midpoint(self):
        # min=20000, max=60000, budget=40000 → 0.6 + 0.4*(20000/40000) = 0.8
        result = capex_fit(40_000, 20_000, 60_000)
        assert math.isclose(result, 0.8, abs_tol=1e-9)

    def test_budget_at_min(self):
        assert math.isclose(capex_fit(20_000, 20_000, 60_000), 0.6, abs_tol=1e-9)

    def test_budget_at_max(self):
        assert capex_fit(60_000, 20_000, 60_000) == 1.0

    def test_min_equals_max(self):
        assert capex_fit(50_000, 50_000, 50_000) == 1.0

    def test_budget_below_equal_min_max(self):
        assert capex_fit(30_000, 50_000, 50_000) == 0.0


class TestTimeFit:
    def test_horizon_above_max(self):
        assert time_fit(36, 6, 12) == 1.0

    def test_horizon_below_min(self):
        assert time_fit(2, 6, 12) == 0.0

    def test_horizon_at_midpoint(self):
        # min=6, max=12, horizon=9 → 0.6 + 0.4*(3/6) = 0.8
        result = time_fit(9, 6, 12)
        assert math.isclose(result, 0.8, abs_tol=1e-9)

    def test_min_equals_max(self):
        assert time_fit(6, 6, 6) == 1.0


class TestProfitFit:
    def test_all_levels(self):
        assert profit_fit("LOW") == 0.3
        assert profit_fit("MED") == 0.6
        assert profit_fit("HIGH") == 0.85
        assert profit_fit("VERY_HIGH") == 0.95

    def test_unknown_defaults(self):
        assert profit_fit("UNKNOWN") == 0.3


class TestRiskFit:
    def test_low_tolerance_low_risk(self):
        assert risk_fit("LOW", "LOW") == 1.0

    def test_low_tolerance_high_risk(self):
        assert risk_fit("LOW", "HIGH") == 0.2

    def test_high_tolerance_high_risk(self):
        assert risk_fit("HIGH", "HIGH") == 1.0

    def test_med_tolerance_med_risk(self):
        assert risk_fit("MED", "MED") == 1.0


class TestNormalizeWeights:
    def test_already_normalized(self):
        w = {"a": 0.5, "b": 0.5}
        result = normalize_weights(w)
        assert math.isclose(sum(result.values()), 1.0)

    def test_unnormalized(self):
        w = {"a": 2.0, "b": 3.0}
        result = normalize_weights(w)
        assert math.isclose(result["a"], 0.4)
        assert math.isclose(result["b"], 0.6)

    def test_all_zeros(self):
        w = {"a": 0.0, "b": 0.0}
        result = normalize_weights(w)
        assert math.isclose(result["a"], 0.5)
        assert math.isclose(result["b"], 0.5)


class TestWeightedSum:
    def test_basic(self):
        fits = {"profit": 0.8, "risk": 0.6}
        weights = {"profit": 0.5, "risk": 0.5}
        result = weighted_sum(fits, weights)
        assert math.isclose(result, 0.7, abs_tol=1e-9)

    def test_partial_overlap(self):
        fits = {"profit": 1.0, "extra": 0.5}
        weights = {"profit": 1.0, "risk": 0.5}
        # Only "profit" overlaps → 1.0*1.0 = 1.0
        assert math.isclose(weighted_sum(fits, weights), 1.0)
