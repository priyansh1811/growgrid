/** API types aligned with backend (PlanRequest, PlanResponse, clarification). */

export type CategoryOption = 'general' | 'obc' | 'sc' | 'st'

export interface FormInputs {
  name: string
  email: string
  category: CategoryOption
  location: string
  land_area_acres: number
  water_availability: string
  irrigation_source: string
  budget_total_inr: number
  labour_availability: string
  goal: string
  time_horizon_years: number
  risk_tolerance: string
  /** Month (1–12) when farmer plans to start; used for season-aware recommendations. */
  planning_month?: number | null
}

export interface ClarificationQuestion {
  id: string
  question: string
  suggested_options: string[] | null
}

export interface ClarificationResult {
  clarification_needed: boolean
  questions: ClarificationQuestion[]
  message: string | null
}

export interface RefinementResult {
  suggested_goal: string | null
  suggested_risk_tolerance: string | null
  user_context: string | null
}

export interface HardConstraint {
  dimension: string
  operator: string
  threshold: string
  reason: string
}

export interface PracticeScore {
  practice_code: string
  practice_name: string
  fit_scores: Record<string, number>
  weighted_score: number
  eliminated: boolean
  elimination_reason?: string
}

export interface CropScore {
  crop_id: string
  crop_name: string
  fit_scores: Record<string, number>
  compatibility_score: number
  final_score: number
  eliminated: boolean
  elimination_reason?: string
}

export interface CropPortfolioEntry {
  crop_id: string
  crop_name: string
  area_fraction: number
  role_hint: string
  score: number
}

export interface GrowGuide {
  crop_id: string
  crop_name: string
  sowing_window: string
  monthly_timeline: string[]
  land_prep: string
  irrigation_rules: string
  fertilizer_plan: string
  pest_prevention: string[]
  harvest_notes: string
  why_recommended: string
  when_not_recommended: string
}

export interface AgronomistVerification {
  confidence_score: number
  warnings: string[]
  required_actions: string[]
  citations: string[]
}

export interface ValidatedProfile {
  location: string
  land_area_acres: number
  water_availability: string
  labour_availability: string
  budget_per_acre: number
  horizon_months: number
  goal?: string
  time_horizon_years?: number
  risk_tolerance?: string
  irrigation_source?: string
  budget_total_inr?: number
  user_context?: string | null
}

export interface SoftConstraint {
  dimension: string
  preference: string
  penalty?: number
  reason: string
}

// ── Critic / Consistency Review ──────────────────────────────────────

export interface CriticIssue {
  severity: 'CRITICAL' | 'WARNING' | 'INFO'
  dimension: string
  description: string
  affected_item: string
  suggested_fix?: string | null
}

export interface CriticReport {
  issues: CriticIssue[]
  fixes_applied: string[]
  final_confidence: number
  summary: string
}

// ── Report Composer ─────────────────────────────────────────────────

export interface ReportSection {
  title: string
  content: unknown
}

export interface ReportPayload {
  executive_summary: string
  sections: ReportSection[]
  generated_at: string
}

// ── Economics ────────────────────────────────────────────────────────

export interface CostComponent {
  component: string
  cost_type: string
  avg_inr_per_acre: number
}

export interface CostBreakdown {
  crop_id: string
  crop_name: string
  capex_per_acre: number
  opex_per_acre: number
  total_cost: number
  components: CostComponent[]
}

export interface ROISummary {
  scenario: string
  revenue: number
  total_cost: number
  profit: number
  roi_pct: number
  breakeven_months?: number | null
}

export interface SensitivityResult {
  factor: string
  adjusted_roi_pct: number
  still_profitable: boolean
}

export interface EconomicsReport {
  cost_breakdown: CostBreakdown[]
  roi_summary: ROISummary[]
  sensitivity: SensitivityResult[]
  total_capex: number
  total_opex: number
  data_coverage: number
}

// ── Field Layout ────────────────────────────────────────────────────

export interface FieldBlock {
  crop_id: string
  crop_name: string
  area_acres: number
  row_spacing_cm: number
  plant_spacing_cm: number
  total_plants: number
  rows: number
  plants_per_row: number
  block_label: string
}

export interface FieldLayoutPlan {
  blocks: FieldBlock[]
  total_area_used_acres: number
  notes: string[]
}

// ── Government Schemes ──────────────────────────────────────────────

export interface MatchedScheme {
  scheme_id: string
  scheme_name: string
  relevance_score: number
  subsidy_pct?: number | null
  max_subsidy_inr?: number | null
  eligibility_summary: string
  application_url?: string | null
  match_reasons: string[]
}

export interface SchemesReport {
  matched_schemes: MatchedScheme[]
  total_potential_subsidy?: number | null
  eligibility_checklist: string[]
  data_note: string
}

// ── Plan Response (full pipeline output) ────────────────────────────

export interface PlanResponse {
  validated_profile: ValidatedProfile
  hard_constraints: HardConstraint[]
  soft_constraints: SoftConstraint[]
  warnings: string[]
  conflicts: string[]
  goal_weights: Record<string, number>
  goal_explanation: string
  practice_ranking: PracticeScore[]
  selected_practice: PracticeScore
  practice_alternatives: PracticeScore[]
  selected_practice_reason?: string
  crop_ranking: CropScore[]
  selected_crop_portfolio: CropPortfolioEntry[]
  selected_crop_portfolio_reason?: string
  agronomist_verification: AgronomistVerification
  grow_guides: GrowGuide[]
  // Phase 1 additions
  critic_report?: CriticReport | null
  report_payload?: ReportPayload | null
  economics?: EconomicsReport | null
  field_layout?: FieldLayoutPlan | null
  schemes?: SchemesReport | null
}
