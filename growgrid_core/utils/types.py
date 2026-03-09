"""Pydantic models for request / response / internal state."""

from __future__ import annotations

from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, model_validator

from growgrid_core.utils.enums import (
    ConflictLevel,
    Goal,
    IrrigationSource,
    LabourLevel,
    RiskLevel,
    WaterLevel,
)

# ── Request ──────────────────────────────────────────────────────────────


class PlanValidationError(Exception):
    """Raised by ValidationAgent when request fails sanity checks. Carries a list of error messages."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class PlanRequest(BaseModel):
    location: str = Field(..., min_length=1, description="State + District")
    land_area_acres: float = Field(..., gt=0)
    water_availability: WaterLevel
    irrigation_source: IrrigationSource
    budget_total_inr: int = Field(..., gt=0)
    labour_availability: LabourLevel
    goal: Goal
    time_horizon_years: float = Field(..., gt=0)
    risk_tolerance: RiskLevel
    user_context: str | None = Field(
        default=None,
        description="Optional context from clarification (e.g. trial plot, first-time farmer) for downstream agents",
    )
    planning_month: int | None = Field(
        default=None,
        ge=1,
        le=12,
        description="Month (1–12) when farmer plans to start; used for season-aware crop filtering.",
    )

    @model_validator(mode="after")
    def validate_cross_field(self) -> "PlanRequest":
        """Catch simple contradictions at parse time; domain rules stay in ValidationAgent."""
        if not (self.location or "").strip():
            raise ValueError("Location is required.")
        if self.land_area_acres <= 0:
            raise ValueError("Land area must be > 0 acres.")
        if self.budget_total_inr <= 0:
            raise ValueError("Budget must be > 0 INR.")
        if self.time_horizon_years <= 0:
            raise ValueError("Time horizon must be > 0 years.")
        return self


# ── Validated profile ────────────────────────────────────────────────────


class ValidatedProfile(BaseModel):
    location: str
    land_area_acres: float
    water_availability: WaterLevel
    irrigation_source: IrrigationSource
    budget_total_inr: int
    labour_availability: LabourLevel
    goal: Goal
    time_horizon_years: float
    risk_tolerance: RiskLevel
    # Derived
    budget_per_acre: float
    horizon_months: int
    user_context: str | None = None
    planning_month: int | None = None  # 1–12 when farmer plans to start


# ── Constraints ──────────────────────────────────────────────────────────

# A small, strict schema makes downstream filtering deterministic and less bug-prone.
ConstraintDimension = Literal[
    "water",
    "labour",
    "budget",
    "risk",
    "time",
    "horizon",
    "irrigation",
    "practice",
    "crop",
]

HardOperator = Literal[
    # compare a candidate attribute against a value
    "exclude_if_equal",
    "exclude_if_above",
    "exclude_if_below",
    # direct allow/deny lists (useful for protected cultivation, orchard-only, etc.)
    "exclude_practice_codes",
    "exclude_crop_ids",
]


class HardConstraint(BaseModel):
    dimension: ConstraintDimension
    operator: HardOperator
    # Used for threshold comparisons OR comma-separated lists for exclude_* lists.
    threshold: str
    reason: str


class SoftConstraint(BaseModel):
    """A preference/penalty that can be applied during scoring (not elimination)."""

    dimension: ConstraintDimension
    preference: str  # e.g. "prefer_rainfed", "penalise_high_water"
    penalty: float = 0.0  # 0..1 (optional), used by scoring layers
    reason: str


# ── Weights ──────────────────────────────────────────────────────────────


class WeightVector(BaseModel):
    model_config = {"extra": "forbid"}
    profit: float
    risk: float
    water: float
    labour: float
    time: float
    capex: float

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()


# ── Practice scoring ─────────────────────────────────────────────────────


class PracticeScore(BaseModel):
    practice_code: str
    practice_name: str
    fit_scores: dict[str, float]  # dimension -> 0..1
    weighted_score: float
    eliminated: bool = False
    elimination_reason: Optional[str] = None


# ── Crop scoring ─────────────────────────────────────────────────────────


class CropScore(BaseModel):
    crop_id: str
    crop_name: str
    fit_scores: dict[str, float]
    compatibility_score: float
    final_score: float
    eliminated: bool = False
    elimination_reason: Optional[str] = None


class CropPortfolioEntry(BaseModel):
    crop_id: str
    crop_name: str
    area_fraction: float
    role_hint: str
    score: float


# ── Agronomist verification ─────────────────────────────────────────────


class EvidenceCard(BaseModel):
    claim: str
    source_url: str = ""
    snippet: str = ""
    conflict_level: ConflictLevel = ConflictLevel.NO_ISSUE


class GrowGuide(BaseModel):
    crop_id: str
    crop_name: str
    sowing_window: str
    monthly_timeline: list[str]
    land_prep: str
    irrigation_rules: str
    fertilizer_plan: str
    pest_prevention: list[str]
    harvest_notes: str
    why_recommended: str
    when_not_recommended: str


class AgronomistVerification(BaseModel):
    verified_practice: Optional[PracticeScore] = None
    verified_crop_portfolio: list[CropPortfolioEntry] = Field(default_factory=list)
    confidence_score: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)


# ── Full response ────────────────────────────────────────────────────────


class PlanResponse(BaseModel):
    validated_profile: ValidatedProfile
    hard_constraints: list[HardConstraint]
    soft_constraints: list[SoftConstraint]
    warnings: list[str]
    conflicts: list[str] = Field(default_factory=list)
    goal_weights: WeightVector
    goal_explanation: str
    practice_ranking: list[PracticeScore]
    selected_practice: PracticeScore
    practice_alternatives: list[PracticeScore]
    selected_practice_reason: str = ""
    crop_ranking: list[CropScore]
    selected_crop_portfolio: list[CropPortfolioEntry]
    selected_crop_portfolio_reason: str = ""
    agronomist_verification: AgronomistVerification
    grow_guides: list[GrowGuide]
