"""Pydantic models for request / response / internal state."""

from __future__ import annotations

from typing import Any, Literal, Optional

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
    name: str | None = Field(default=None, description="User's name (for email delivery)")
    email: str | None = Field(default=None, description="User's email (for email delivery)")
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


# ── Critic report ───────────────────────────────────────────────────────


class CriticIssue(BaseModel):
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    dimension: str  # water, budget, horizon, labour, perishability, irrigation, etc.
    description: str
    affected_item: str  # practice_code or crop_id
    suggested_fix: Optional[str] = None


class CriticReport(BaseModel):
    issues: list[CriticIssue] = Field(default_factory=list)
    fixes_applied: list[str] = Field(default_factory=list)
    final_confidence: float = 1.0  # 0..1 — reduced per issue severity
    summary: str = ""


# ── Report payload ──────────────────────────────────────────────────────


class ReportSection(BaseModel):
    title: str
    content: Any  # structured data for rendering


class ReportPayload(BaseModel):
    executive_summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    generated_at: str = ""


# ── Economics ───────────────────────────────────────────────────────────


class CostBreakdown(BaseModel):
    crop_id: str
    crop_name: str
    capex_per_acre: float = 0.0
    opex_per_acre: float = 0.0
    total_cost: float = 0.0
    components: list[dict[str, Any]] = Field(default_factory=list)


class ROISummary(BaseModel):
    scenario: str  # "best", "base", "worst"
    revenue: float = 0.0
    total_cost: float = 0.0
    profit: float = 0.0
    roi_pct: float = 0.0
    breakeven_months: Optional[float] = None


class SensitivityResult(BaseModel):
    factor: str  # "price_-15%", "yield_-10%", "labour_+10%"
    adjusted_roi_pct: float = 0.0
    still_profitable: bool = True


class EconomicsReport(BaseModel):
    cost_breakdown: list[CostBreakdown] = Field(default_factory=list)
    roi_summary: list[ROISummary] = Field(default_factory=list)
    sensitivity: list[SensitivityResult] = Field(default_factory=list)
    total_capex: float = 0.0
    total_opex: float = 0.0
    data_coverage: float = 0.0  # 0..1 — fraction of crops with cost data


# ── Field layout ────────────────────────────────────────────────────────


class FieldBlock(BaseModel):
    crop_id: str
    crop_name: str
    area_acres: float
    row_spacing_cm: float = 0.0
    plant_spacing_cm: float = 0.0
    total_plants: int = 0
    rows: int = 0
    plants_per_row: int = 0
    block_label: str = ""


class FieldLayoutPlan(BaseModel):
    blocks: list[FieldBlock] = Field(default_factory=list)
    total_area_used_acres: float = 0.0
    notes: list[str] = Field(default_factory=list)


# ── Government schemes ──────────────────────────────────────────────────


class MatchedScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    relevance_score: float = 0.0
    subsidy_pct: Optional[float] = None
    max_subsidy_inr: Optional[float] = None
    eligibility_summary: str = ""
    application_url: Optional[str] = None
    match_reasons: list[str] = Field(default_factory=list)


class SchemesReport(BaseModel):
    matched_schemes: list[MatchedScheme] = Field(default_factory=list)
    total_potential_subsidy: Optional[float] = None
    eligibility_checklist: list[str] = Field(default_factory=list)
    data_note: str = ""


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
    # Phase-1 additions (optional for backward compatibility)
    critic_report: Optional[CriticReport] = None
    report_payload: Optional[ReportPayload] = None
    economics: Optional[EconomicsReport] = None
    field_layout: Optional[FieldLayoutPlan] = None
    schemes: Optional[SchemesReport] = None
