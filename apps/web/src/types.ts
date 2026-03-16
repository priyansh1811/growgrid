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
  annualized_roi_pct: number
  capital_required: number
  peak_cash_deficit: number
  payback_status: string
  breakeven_months?: number | null
}

export interface SensitivityResult {
  factor: string
  description: string
  adjusted_roi_pct: number
  adjusted_revenue: number
  adjusted_cost: number
  adjusted_profit: number
  still_profitable: boolean
}

export interface SanityCheckItem {
  field: string
  status: 'OK' | 'WARNING' | 'SUSPICIOUS'
  message: string
}

export interface SanityCheckReport {
  overall_status: 'PASSED' | 'WARNINGS' | 'FAILED'
  checks: SanityCheckItem[]
  summary: string
}

export interface RevenueSummary {
  best_annual: number
  base_annual: number
  worst_annual: number
  best_total: number
  base_total: number
  worst_total: number
}

export interface ProfitSummary {
  best: number
  base: number
  worst: number
}

export interface BreakEvenSummary {
  best_months: number | null
  base_months: number | null
  worst_months: number | null
  best_status?: string
  base_status?: string
  worst_status?: string
}

export interface GraphPayload {
  roi_chart: Array<{
    scenario: string
    scenario_key: string
    revenue: number
    cost: number
    profit: number
    roi_pct: number
    annualized_roi_pct?: number
    capital_required?: number
  }>
  scenario_comparison?: Array<{
    scenario: string
    revenue: number
    cost: number
    profit: number
    roi_percent?: number
  }>
  monthly_cashflow?: Array<{
    month: number
    expense: number
    revenue: number
    net: number
    cumulative: number
  }>
  cost_chart: Array<{
    crop_name: string
    capex: number
    opex: number
    total: number
  }>
  sensitivity_chart: Array<{
    factor: string
    adjusted_roi: number
    still_profitable: boolean
  }>
  breakeven_chart: Array<{
    scenario: string
    months: number
    status?: string
  }>
  cost_composition: Array<{
    name: string
    value: number
    pct: number
  }>
}

export interface UISummaryCard {
  label: string
  value: number | null
  unit: string
  color: string
}

export interface UIPayload {
  summary_cards: UISummaryCard[]
  assumptions: string[]
  warnings: string[]
  data_coverage_pct: number
}

export interface EconomicsReport {
  cost_breakdown: CostBreakdown[]
  roi_summary: ROISummary[]
  sensitivity: SensitivityResult[]
  total_capex: number
  total_opex: number
  total_annual_opex: number
  data_coverage: number
  revenue_summary: RevenueSummary
  profit_summary: ProfitSummary
  break_even: BreakEvenSummary
  assumptions_used: string[]
  warnings: string[]
  sanity_check?: SanityCheckReport | null
  graph_payload?: GraphPayload | null
  ui_payload?: UIPayload | null
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
  // Expert-level fields
  planting_pattern?: string
  planting_depth_cm?: number
  field_length_m?: number
  field_width_m?: number
  bed_type?: string
  seed_rate_hint?: string
  irrigation_method?: string
  companion_crops?: string[]
  planting_tip?: string
}

export interface FieldLayoutPlan {
  blocks: FieldBlock[]
  total_area_used_acres: number
  notes: string[]
  // Expert planning additions
  field_orientation?: string
  pathway_width_m?: number
  border_crop?: string
  irrigation_layout?: string
  expert_tips?: string[]
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

// ── Economist v2 Output ──────────────────────────────────────────────

export interface CropScenarioResult {
  crop_id: string
  crop_name: string
  area_acres: number
  setup_cost_per_acre: number
  operating_cost_per_acre: number
  gross_revenue_per_acre: number
  net_profit_per_acre: number
  yield_per_acre: number
  price_per_unit: number
  loss_pct: number
}

export interface ScenarioPnL {
  scenario: string
  crops: CropScenarioResult[]
  total_setup_cost: number
  total_operating_cost: number
  total_revenue: number
  total_profit: number
  roi_percent: number
  break_even_months?: number | null
  break_even_years?: number | null
  break_even_status: string
}

export interface MonthlyCashflow {
  month: number
  operating_expense: number
  revenue: number
  net_cash: number
  cumulative_position: number
}

export interface WorkingCapitalGap {
  exists: boolean
  amount: number
  months: number[]
}

export interface SensitivityRow {
  factor: string
  description: string
  adjusted_revenue: number
  adjusted_cost: number
  adjusted_profit: number
  adjusted_roi_percent: number
  still_profitable: boolean
}

export interface PriceSource {
  crop: string
  source: string
  confidence: string
  fetch_date: string
  price_min?: number | null
  price_max?: number | null
}

export interface DataQualityReport {
  overall_quality: string
  fields_from_live_fetch: string[]
  fields_from_database: string[]
  fields_from_fallback: string[]
  lowest_confidence_assumption: string
}

export interface EconomistOutput {
  scenarios: Record<string, ScenarioPnL>
  monthly_cashflow_year1: MonthlyCashflow[]
  working_capital_gap?: WorkingCapitalGap | null
  sensitivity_analysis: SensitivityRow[]
  break_even: Record<string, unknown>
  financial_narrative?: string | null
  data_quality_summary?: DataQualityReport | null
  price_sources: PriceSource[]
  assumptions_used: string[]
  warnings: string[]
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
  economist_output?: EconomistOutput | null
  field_layout?: FieldLayoutPlan | null
  schemes?: SchemesReport | null
}
