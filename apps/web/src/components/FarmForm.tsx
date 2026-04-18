import type { FormInputs } from '../api/client'
import { FormWizard } from './form/FormWizard'

/* ───── Option constants (exported for FormWizard step components) ───── */

export const CATEGORY_OPTS: { value: FormInputs['category']; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'obc', label: 'OBC' },
  { value: 'sc', label: 'SC' },
  { value: 'st', label: 'ST' },
]

export const WATER_OPTS = [
  { value: 'LOW' as const, label: 'Low', hint: 'Rain-fed only, limited access' },
  { value: 'MED' as const, label: 'Medium', hint: 'Seasonal irrigation available' },
  { value: 'HIGH' as const, label: 'High', hint: 'Perennial source, year-round' },
]

export const IRRIGATION_OPTS = [
  { value: 'NONE' as const, label: 'None (Rain-fed)' },
  { value: 'CANAL' as const, label: 'Canal' },
  { value: 'BOREWELL' as const, label: 'Borewell' },
  { value: 'DRIP' as const, label: 'Drip' },
  { value: 'MIXED' as const, label: 'Mixed' },
]

export const LABOUR_OPTS = [
  { value: 'LOW' as const, label: 'Low', hint: 'Family labour only, 1-2 people' },
  { value: 'MED' as const, label: 'Medium', hint: '3-5 workers available' },
  { value: 'HIGH' as const, label: 'High', hint: '5+ workers or mechanized' },
]

export const GOAL_OPTS = [
  { value: 'MAXIMIZE_PROFIT' as const, label: 'Maximize Profit', hint: 'Focus on highest returns' },
  { value: 'STABLE_INCOME' as const, label: 'Stable Income', hint: 'Consistent, low-risk earnings' },
  { value: 'WATER_SAVING' as const, label: 'Water Saving', hint: 'Minimize water consumption' },
  { value: 'FAST_ROI' as const, label: 'Fast ROI', hint: 'Quick returns on investment' },
]

export const RISK_OPTS = [
  { value: 'LOW' as const, label: 'Low', hint: 'Prefer safe, proven crops' },
  { value: 'MED' as const, label: 'Medium', hint: 'Balanced risk-reward' },
  { value: 'HIGH' as const, label: 'High', hint: 'Open to experimental/high-reward' },
]

export const MONTH_OPTS = [
  { value: 0, label: 'Auto-detect' },
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
]

/* ───── FarmForm shell ───── */

interface FarmFormProps {
  form: FormInputs
  onChange: (f: FormInputs) => void
  onGenerate: () => void
  loading: boolean
}

export function FarmForm({ form, onChange, onGenerate, loading }: FarmFormProps) {
  return <FormWizard form={form} onChange={onChange} onGenerate={onGenerate} loading={loading} />
}
