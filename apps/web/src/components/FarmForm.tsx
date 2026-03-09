import type { FormInputs } from '../api/client'

const CATEGORY_OPTS: { value: FormInputs['category']; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'obc', label: 'OBC' },
  { value: 'sc', label: 'SC' },
  { value: 'st', label: 'ST' },
]
const WATER_OPTS = ['LOW', 'MED', 'HIGH']
const IRRIGATION_OPTS = ['NONE', 'CANAL', 'BOREWELL', 'DRIP', 'MIXED']
const LABOUR_OPTS = ['LOW', 'MED', 'HIGH']
const GOAL_OPTS = [
  { value: 'MAXIMIZE_PROFIT', label: 'Maximize Profit' },
  { value: 'STABLE_INCOME', label: 'Stable Income' },
  { value: 'WATER_SAVING', label: 'Water Saving' },
  { value: 'FAST_ROI', label: 'Fast ROI' },
]
const RISK_OPTS = ['LOW', 'MED', 'HIGH']

interface FarmFormProps {
  form: FormInputs
  onChange: (f: FormInputs) => void
  onGenerate: () => void
  loading: boolean
}

export function FarmForm({ form, onChange, onGenerate, loading }: FarmFormProps) {
  const update = (k: keyof FormInputs, v: string | number) =>
    onChange({ ...form, [k]: v })

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
      <h1 className="mb-2 text-xl font-semibold text-slate-800">
        Farm details
      </h1>
      <p className="mb-6 text-sm text-surface-500">
        Enter your details and farm parameters to get practice and crop recommendations.
      </p>

      <div className="mb-6 rounded-lg border border-surface-200 bg-surface-50/50 p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Your details</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => update('email', e.target.value)}
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Category</label>
            <select
              value={form.category}
              onChange={(e) => update('category', e.target.value as FormInputs['category'])}
              className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              {CATEGORY_OPTS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Location (State, District)
          </label>
          <input
            type="text"
            value={form.location}
            onChange={(e) => update('location', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            placeholder="e.g. Karnataka, Bangalore Rural"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Land area (acres)
          </label>
          <input
            type="number"
            min={0.1}
            max={1000}
            step={0.5}
            value={form.land_area_acres}
            onChange={(e) => update('land_area_acres', parseFloat(e.target.value) || 0)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Water availability
          </label>
          <select
            value={form.water_availability}
            onChange={(e) => update('water_availability', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {WATER_OPTS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Irrigation source
          </label>
          <select
            value={form.irrigation_source}
            onChange={(e) => update('irrigation_source', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {IRRIGATION_OPTS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Total budget (INR)
          </label>
          <input
            type="number"
            min={1000}
            max={100_000_000}
            step={10000}
            value={form.budget_total_inr}
            onChange={(e) => update('budget_total_inr', parseInt(e.target.value, 10) || 0)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Labour availability
          </label>
          <select
            value={form.labour_availability}
            onChange={(e) => update('labour_availability', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {LABOUR_OPTS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Primary goal
          </label>
          <select
            value={form.goal}
            onChange={(e) => update('goal', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {GOAL_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Time horizon (years)
          </label>
          <input
            type="number"
            min={0.1}
            max={30}
            step={0.5}
            value={form.time_horizon_years}
            onChange={(e) => update('time_horizon_years', parseFloat(e.target.value) || 0)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Risk tolerance
          </label>
          <select
            value={form.risk_tolerance}
            onChange={(e) => update('risk_tolerance', e.target.value)}
            className="w-full rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            {RISK_OPTS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-8">
        <button
          type="button"
          onClick={onGenerate}
          disabled={loading}
          className="rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-60"
        >
          {loading ? 'Checking…' : 'Generate plan'}
        </button>
      </div>
    </div>
  )
}
