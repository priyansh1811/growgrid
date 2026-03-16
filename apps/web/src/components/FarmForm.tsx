import { type ReactNode } from 'react'
import type { FormInputs } from '../api/client'

const CATEGORY_OPTS: { value: FormInputs['category']; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'obc', label: 'OBC' },
  { value: 'sc', label: 'SC' },
  { value: 'st', label: 'ST' },
]
const WATER_OPTS = [
  { value: 'LOW', label: 'Low', hint: 'Rain-fed only, limited access' },
  { value: 'MED', label: 'Medium', hint: 'Seasonal irrigation available' },
  { value: 'HIGH', label: 'High', hint: 'Perennial source, year-round' },
]
const IRRIGATION_OPTS = [
  { value: 'NONE', label: 'None (Rain-fed)' },
  { value: 'CANAL', label: 'Canal' },
  { value: 'BOREWELL', label: 'Borewell' },
  { value: 'DRIP', label: 'Drip' },
  { value: 'MIXED', label: 'Mixed' },
]
const LABOUR_OPTS = [
  { value: 'LOW', label: 'Low', hint: 'Family labour only, 1-2 people' },
  { value: 'MED', label: 'Medium', hint: '3-5 workers available' },
  { value: 'HIGH', label: 'High', hint: '5+ workers or mechanized' },
]
const GOAL_OPTS = [
  { value: 'MAXIMIZE_PROFIT', label: 'Maximize Profit', hint: 'Focus on highest returns' },
  { value: 'STABLE_INCOME', label: 'Stable Income', hint: 'Consistent, low-risk earnings' },
  { value: 'WATER_SAVING', label: 'Water Saving', hint: 'Minimize water consumption' },
  { value: 'FAST_ROI', label: 'Fast ROI', hint: 'Quick returns on investment' },
]
const RISK_OPTS = [
  { value: 'LOW', label: 'Low', hint: 'Prefer safe, proven crops' },
  { value: 'MED', label: 'Medium', hint: 'Balanced risk-reward' },
  { value: 'HIGH', label: 'High', hint: 'Open to experimental/high-reward' },
]
const MONTH_OPTS = [
  { value: 0, label: 'Auto-detect' },
  { value: 1, label: 'January' }, { value: 2, label: 'February' },
  { value: 3, label: 'March' }, { value: 4, label: 'April' },
  { value: 5, label: 'May' }, { value: 6, label: 'June' },
  { value: 7, label: 'July' }, { value: 8, label: 'August' },
  { value: 9, label: 'September' }, { value: 10, label: 'October' },
  { value: 11, label: 'November' }, { value: 12, label: 'December' },
]

interface FarmFormProps {
  form: FormInputs
  onChange: (f: FormInputs) => void
  onGenerate: () => void
  loading: boolean
}

function FieldGroup({
  label,
  tooltip,
  children,
  error,
}: {
  label: string
  tooltip?: string
  children: ReactNode
  error?: string
}) {
  return (
    <div>
      <label className="mb-1 flex items-center gap-1 text-sm font-medium text-slate-700">
        {label}
        {tooltip && (
          <span className="group relative">
            <span className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-surface-200 text-[10px] font-bold text-slate-500">
              ?
            </span>
            <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-800 px-2.5 py-1.5 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100">
              {tooltip}
            </span>
          </span>
        )}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

const inputClass =
  'w-full rounded-lg border border-surface-300 px-3 py-2 text-sm transition-colors focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500'

export function FarmForm({ form, onChange, onGenerate, loading }: FarmFormProps) {
  const update = (k: keyof FormInputs, v: string | number | null) =>
    onChange({ ...form, [k]: v })

  const errors: Partial<Record<keyof FormInputs, string>> = {}
  if (form.land_area_acres <= 0) errors.land_area_acres = 'Must be greater than 0'
  if (form.budget_total_inr <= 0) errors.budget_total_inr = 'Must be greater than 0'
  if (form.time_horizon_years <= 0) errors.time_horizon_years = 'Must be greater than 0'
  if (!form.location.trim()) errors.location = 'Location is required'

  const hasErrors = Object.keys(errors).length > 0

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
      <h1 className="mb-2 text-xl font-semibold text-slate-800">
        Farm Details
      </h1>
      <p className="mb-6 text-sm text-surface-500">
        Enter your details and farm parameters to get AI-powered practice and crop recommendations.
      </p>

      {/* Personal details */}
      <div className="mb-6 rounded-lg border border-surface-200 bg-surface-50/50 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Your Details</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <FieldGroup label="Name">
            <input
              type="text"
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              className={inputClass}
              placeholder="Your name"
            />
          </FieldGroup>
          <FieldGroup label="Email">
            <input
              type="email"
              value={form.email}
              onChange={(e) => update('email', e.target.value)}
              className={inputClass}
              placeholder="you@example.com"
            />
          </FieldGroup>
          <FieldGroup label="Category" tooltip="Social category for scheme eligibility matching">
            <select
              value={form.category}
              onChange={(e) => update('category', e.target.value as FormInputs['category'])}
              className={inputClass}
            >
              {CATEGORY_OPTS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </FieldGroup>
        </div>
      </div>

      {/* Farm parameters */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <FieldGroup
          label="Location (State, District)"
          tooltip="Used for climate matching, scheme eligibility, and crop suitability"
          error={errors.location}
        >
          <input
            type="text"
            value={form.location}
            onChange={(e) => update('location', e.target.value)}
            className={`${inputClass} ${errors.location ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
            placeholder="e.g. Karnataka, Bangalore Rural"
          />
        </FieldGroup>

        <FieldGroup
          label="Land Area (acres)"
          tooltip="Total cultivable land. Affects crop diversity and practice feasibility."
          error={errors.land_area_acres}
        >
          <input
            type="number"
            min={0.1}
            max={1000}
            step={0.5}
            value={form.land_area_acres}
            onChange={(e) => update('land_area_acres', parseFloat(e.target.value) || 0)}
            className={`${inputClass} ${errors.land_area_acres ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
          />
        </FieldGroup>

        <FieldGroup
          label="Water Availability"
          tooltip="Overall water access level. Affects which crops and practices are viable."
        >
          <select
            value={form.water_availability}
            onChange={(e) => update('water_availability', e.target.value)}
            className={inputClass}
          >
            {WATER_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label} — {o.hint}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup
          label="Irrigation Source"
          tooltip="Primary irrigation method. Determines practice eligibility (e.g. drip for polyhouse)."
        >
          <select
            value={form.irrigation_source}
            onChange={(e) => update('irrigation_source', e.target.value)}
            className={inputClass}
          >
            {IRRIGATION_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup
          label="Total Budget (INR)"
          tooltip="Entire farming budget including CAPEX and OPEX. Per-acre budget is computed automatically."
          error={errors.budget_total_inr}
        >
          <input
            type="number"
            min={1000}
            max={100_000_000}
            step={10000}
            value={form.budget_total_inr}
            onChange={(e) => update('budget_total_inr', parseInt(e.target.value, 10) || 0)}
            className={`${inputClass} ${errors.budget_total_inr ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
          />
          {form.land_area_acres > 0 && form.budget_total_inr > 0 && (
            <p className="mt-1 text-xs text-slate-400">
              {`\u20B9${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(form.budget_total_inr / form.land_area_acres)}/acre`}
            </p>
          )}
        </FieldGroup>

        <FieldGroup
          label="Labour Availability"
          tooltip="Affects recommendations: high-labour practices need more workers."
        >
          <select
            value={form.labour_availability}
            onChange={(e) => update('labour_availability', e.target.value)}
            className={inputClass}
          >
            {LABOUR_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label} — {o.hint}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup
          label="Primary Goal"
          tooltip="Drives the weight distribution across profit, risk, water, labour, time, and capex dimensions."
        >
          <select
            value={form.goal}
            onChange={(e) => update('goal', e.target.value)}
            className={inputClass}
          >
            {GOAL_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label} — {o.hint}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup
          label="Time Horizon (years)"
          tooltip="Planning period. Short horizons exclude long-gestation crops like orchards."
          error={errors.time_horizon_years}
        >
          <input
            type="number"
            min={0.5}
            max={30}
            step={0.5}
            value={form.time_horizon_years}
            onChange={(e) => update('time_horizon_years', parseFloat(e.target.value) || 0)}
            className={`${inputClass} ${errors.time_horizon_years ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}`}
          />
        </FieldGroup>

        <FieldGroup
          label="Risk Tolerance"
          tooltip="Low = safe proven crops only. High = includes experimental or volatile crops."
        >
          <select
            value={form.risk_tolerance}
            onChange={(e) => update('risk_tolerance', e.target.value)}
            className={inputClass}
          >
            {RISK_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label} — {o.hint}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup
          label="Planning Month"
          tooltip="Month when you plan to start. Used for season-aware sowing windows."
        >
          <select
            value={form.planning_month ?? 0}
            onChange={(e) => {
              const v = parseInt(e.target.value, 10)
              update('planning_month', v === 0 ? null : v)
            }}
            className={inputClass}
          >
            {MONTH_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </FieldGroup>
      </div>

      {/* Submit */}
      <div className="mt-8 flex items-center gap-4">
        <button
          type="button"
          onClick={onGenerate}
          disabled={loading || hasErrors}
          className="rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Generating...
            </span>
          ) : (
            'Generate Plan'
          )}
        </button>
        {hasErrors && (
          <p className="text-sm text-red-500">Please fix the errors above before generating.</p>
        )}
      </div>
    </div>
  )
}
