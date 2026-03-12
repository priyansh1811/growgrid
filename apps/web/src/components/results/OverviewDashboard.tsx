import type { PlanResponse } from '../../types'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip,
} from 'recharts'

const CROP_COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#ec4899']

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

const LABEL_MAP: Record<string, string> = {
  profit: 'Profit',
  risk: 'Risk',
  water: 'Water',
  labour: 'Labour',
  time: 'Time',
  capex: 'CAPEX',
}

export function OverviewDashboard({ plan }: { plan: PlanResponse }) {
  const { validated_profile: profile, goal_weights, selected_practice, selected_crop_portfolio } = plan

  // Radar chart data for goal weights
  const radarData = Object.entries(goal_weights).map(([key, value]) => ({
    dimension: LABEL_MAP[key] || key,
    weight: +(value * 100).toFixed(1),
  }))

  // Pie chart data for crop portfolio
  const pieData = selected_crop_portfolio.map((c) => ({
    name: c.crop_name,
    value: +(c.area_fraction * 100).toFixed(1),
    area: +(c.area_fraction * profile.land_area_acres).toFixed(2),
  }))

  const baseROI = plan.economics?.roi_summary?.find((r) => r.scenario === 'base')

  return (
    <div className="space-y-6">
      {/* Executive summary */}
      {plan.report_payload?.executive_summary && (
        <div className="rounded-xl border border-primary-200 bg-primary-50 p-5">
          <p className="text-sm leading-relaxed text-primary-800">{plan.report_payload.executive_summary}</p>
        </div>
      )}

      {/* Key metrics row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Land Area" value={`${profile.land_area_acres} acres`} />
        <MetricCard label="Budget" value={`\u20B9${fmt(profile.budget_total_inr || 0)}`} />
        <MetricCard label="Practice" value={selected_practice.practice_name} />
        <MetricCard
          label="Crops"
          value={`${selected_crop_portfolio.length} selected`}
        />
      </div>

      {baseROI && (
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard label="Expected Revenue" value={`\u20B9${fmt(baseROI.revenue)}`} accent="green" />
          <MetricCard label="Expected ROI" value={`${baseROI.roi_pct.toFixed(1)}%`} accent={baseROI.roi_pct >= 0 ? 'green' : 'red'} />
          <MetricCard
            label="Break-even"
            value={baseROI.breakeven_months != null ? `${baseROI.breakeven_months} months` : 'N/A'}
            accent="blue"
          />
        </div>
      )}

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Goal weights radar */}
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h3 className="mb-2 text-base font-semibold text-slate-800">Goal Weights</h3>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData} outerRadius="75%">
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis tick={{ fontSize: 10 }} domain={[0, 'auto']} />
              <Radar
                dataKey="weight"
                stroke="#6366f1"
                fill="#6366f1"
                fillOpacity={0.25}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Crop area donut */}
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h3 className="mb-2 text-base font-semibold text-slate-800">Crop Area Split</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                dataKey="value"
                nameKey="name"
                label={({ name, value }) => `${name} ${value}%`}
                labelLine={false}
              >
                {pieData.map((_, index) => (
                  <Cell key={index} fill={CROP_COLORS[index % CROP_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value}%`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Warnings & Conflicts */}
      {plan.warnings && plan.warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-amber-900">Warnings</h3>
          <ul className="list-inside list-disc text-sm text-amber-800">
            {plan.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {plan.conflicts && plan.conflicts.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-red-900">Conflicts</h3>
          <ul className="list-inside list-disc text-sm text-red-800">
            {plan.conflicts.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: 'green' | 'red' | 'blue'
}) {
  const valueColor = accent === 'green'
    ? 'text-green-700'
    : accent === 'red'
      ? 'text-red-600'
      : accent === 'blue'
        ? 'text-blue-700'
        : 'text-slate-800'

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-bold ${valueColor}`}>{value}</p>
    </div>
  )
}
