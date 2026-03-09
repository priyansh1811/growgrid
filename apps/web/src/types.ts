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
}
