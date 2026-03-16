"""Pure scoring functions — deterministic, no side-effects."""

from __future__ import annotations

# ── Ordinal mapping ──────────────────────────────────────────────────────

ORDINAL_MAP: dict[str, int] = {"LOW": 0, "MED": 1, "HIGH": 2}


def ordinal_fit(user_level: str, item_level: str) -> float:
    """Return fit score based on ordinal distance.

    - perfect match → 1.0
    - one-step mismatch → 0.6
    - opposite → 0.2
    """
    u = ORDINAL_MAP[user_level]
    i = ORDINAL_MAP[item_level]
    gap = abs(u - i)
    if gap == 0:
        return 1.0
    elif gap == 1:
        return 0.6
    else:
        return 0.2


# ── CAPEX fit ────────────────────────────────────────────────────────────


def capex_fit(budget_per_acre: float, capex_min: float, capex_max: float) -> float:
    """Return capex fit score (0..1).

    - budget >= capex_max → 1.0
    - capex_min <= budget < capex_max → 0.6 + 0.4 * (budget-min)/(max-min)
    - budget < capex_min → 0.0 (should be filtered)
    """
    if budget_per_acre >= capex_max:
        return 1.0
    if budget_per_acre < capex_min:
        return 0.0
    # Avoid division by zero when capex_min == capex_max
    denom = capex_max - capex_min
    if denom == 0:
        return 1.0
    return 0.6 + 0.4 * (budget_per_acre - capex_min) / denom


# ── Time fit ─────────────────────────────────────────────────────────────


def time_fit(horizon_months: int, time_min: int, time_max: int) -> float:
    """Return time fit score (0..1).

    - horizon >= time_max → 1.0
    - time_min <= horizon < time_max → 0.6 + 0.4 * (horizon-min)/(max-min)
    - horizon < time_min → 0.0 (should be filtered)
    """
    if horizon_months >= time_max:
        return 1.0
    if horizon_months < time_min:
        return 0.0
    denom = time_max - time_min
    if denom == 0:
        return 1.0
    return 0.6 + 0.4 * (horizon_months - time_min) / denom


# ── Profit fit ───────────────────────────────────────────────────────────

PROFIT_FIT: dict[str, float] = {
    "LOW": 0.3,
    "MED": 0.6,
    "HIGH": 0.85,
    "VERY_HIGH": 0.95,
}


def profit_fit(potential: str) -> float:
    """Map profit potential label to score."""
    return PROFIT_FIT.get(potential, 0.3)


# ── Risk fit ─────────────────────────────────────────────────────────────

RISK_FIT_MATRIX: dict[str, dict[str, float]] = {
    "LOW": {"LOW": 1.0, "MED": 0.6, "HIGH": 0.2},
    "MED": {"LOW": 0.8, "MED": 1.0, "HIGH": 0.5},
    "HIGH": {"LOW": 0.6, "MED": 0.8, "HIGH": 1.0},
}


def risk_fit(risk_tolerance: str, item_risk: str) -> float:
    """Map (user risk tolerance, item risk level) → fit score."""
    return RISK_FIT_MATRIX.get(risk_tolerance, {}).get(item_risk, 0.5)


# ── Normalization ────────────────────────────────────────────────────────


def normalize_weights(w: dict[str, float]) -> dict[str, float]:
    """Normalize a weight dict so values sum to 1.0."""
    total = sum(w.values())
    if total == 0:
        n = len(w)
        return {k: 1.0 / n for k in w}
    return {k: v / total for k, v in w.items()}


# ── Weighted sum ─────────────────────────────────────────────────────────


def weighted_sum(fits: dict[str, float], weights: dict[str, float]) -> float:
    """Compute Σ(w_dim * fit_dim) for shared keys."""
    score = 0.0
    for dim in fits:
        if dim in weights:
            score += weights[dim] * fits[dim]
    return score
