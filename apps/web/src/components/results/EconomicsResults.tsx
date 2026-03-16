import { useState } from 'react'
import type { EconomicsReport, EconomistOutput } from '../../types'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell, PieChart, Pie,
  LineChart, Line,
} from 'recharts'

const SCENARIO_COLORS: Record<string, string> = {
  optimistic: '#22c55e',
  best: '#22c55e',
  base: '#3b82f6',
  conservative: '#ef4444',
  worst: '#ef4444',
}

const QUALITY_COLORS: Record<string, { bg: string; text: string; border: string; badge: string }> = {
  HIGH: { bg: 'bg-green-50', text: 'text-green-800', border: 'border-green-200', badge: 'bg-green-100 text-green-800' },
  MED: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200', badge: 'bg-amber-100 text-amber-800' },
  LOW: { bg: 'bg-red-50', text: 'text-red-800', border: 'border-red-200', badge: 'bg-red-100 text-red-800' },
}

const PIE_COLORS = ['#6366f1', '#a78bfa']

const fmt = (n: number | null | undefined) =>
  n != null ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n) : '\u2014'

const formatPayback = (months: number | null | undefined, status?: string) => {
  if (status === 'NOT_PROFITABLE') return 'Not reached'
  if (status === 'NOT_REACHED') return 'Not reached'
  if (months == null) return '\u2014'
  return status === 'BEYOND_HORIZON' ? `${months} mo (beyond horizon)` : `${months} mo`
}

type SectionKey = 'overview' | 'costs' | 'revenue' | 'cashflow' | 'sensitivity' | 'data_quality' | 'assumptions'

export function EconomicsResults({
  economics,
  economistOutput,
}: {
  economics: EconomicsReport
  economistOutput?: EconomistOutput | null
}) {
  const {
    cost_breakdown, roi_summary, sensitivity, total_capex, total_opex,
    total_annual_opex, data_coverage, revenue_summary, profit_summary,
    break_even, assumptions_used, warnings, graph_payload, ui_payload,
  } = economics

  const [section, setSection] = useState<SectionKey>('overview')

  const sections: { key: SectionKey; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'costs', label: 'Costs' },
    { key: 'revenue', label: 'Revenue & ROI' },
    { key: 'cashflow', label: 'Cashflow' },
    { key: 'sensitivity', label: 'Sensitivity' },
    { key: 'data_quality', label: 'Data Quality' },
    { key: 'assumptions', label: 'Assumptions' },
  ]

  // Use graph_payload data if available, else derive from raw data
  const roiChartData = graph_payload?.scenario_comparison ?? graph_payload?.roi_chart ?? roi_summary.map((r) => ({
    scenario: r.scenario.charAt(0).toUpperCase() + r.scenario.slice(1),
    scenario_key: r.scenario,
    revenue: r.revenue,
    cost: r.total_cost,
    profit: r.profit,
    roi_pct: r.roi_pct,
  }))

  const costChartData = graph_payload?.cost_chart ?? cost_breakdown.map((c) => ({
    crop_name: c.crop_name,
    capex: c.capex_per_acre,
    opex: c.opex_per_acre,
    total: c.capex_per_acre + c.opex_per_acre,
  }))

  const costComposition = graph_payload?.cost_composition ?? []

  const summaryCards = ui_payload?.summary_cards ?? []
  const bestScenario = roi_summary.find((r) => r.scenario === 'best')
  const baseScenario = roi_summary.find((r) => r.scenario === 'base')
  const worstScenario = roi_summary.find((r) => r.scenario === 'worst')

  // Economist v2 data
  const dq = economistOutput?.data_quality_summary
  const cashflow = economistOutput?.monthly_cashflow_year1 ?? []
  const wcGap = economistOutput?.working_capital_gap
  const narrative = economistOutput?.financial_narrative
  const priceSources = economistOutput?.price_sources ?? []

  return (
    <div className="space-y-6">
      {/* Sub-navigation */}
      <div className="flex gap-1 overflow-x-auto border-b border-surface-200 pb-0">
        {sections.map((s) => (
          <button
            key={s.key}
            type="button"
            onClick={() => setSection(s.key)}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
              section === s.key
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-slate-500 hover:border-surface-300 hover:text-slate-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ─────────────────────────────────────────────── */}
      {section === 'overview' && (
        <div className="space-y-6">
          {/* Summary cards */}
          {summaryCards.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {summaryCards.map((card: { label: string; value: number | null; unit: string; color?: string }, i: number) => (
                <div key={i} className="rounded-xl border border-surface-200 bg-white p-4 text-center shadow-sm">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{card.label}</p>
                  <p className={`mt-1 text-xl font-bold ${
                    card.color === 'red' ? 'text-red-600' :
                    card.color === 'green' || card.color === 'emerald' ? 'text-green-700' :
                    'text-slate-800'
                  }`}>
                    {card.unit === 'INR' && card.value != null ? `\u20B9${fmt(card.value)}` :
                     card.unit === '%' && card.value != null ? `${card.value.toFixed(1)}%` :
                     card.unit === 'months' && card.value != null ? `${card.value} mo` :
                     fmt(card.value)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            /* Fallback summary cards from raw data */
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryCard label="Total CAPEX" value={total_capex} unit="INR" />
              <SummaryCard label="Annual OPEX" value={total_annual_opex || 0} unit="INR" />
              <SummaryCard label="Total OPEX" value={total_opex} unit="INR" />
              <SummaryCard label="Data Coverage" value={Math.round(data_coverage * 100)} unit="%" />
            </div>
          )}

          {/* Financial narrative */}
          {narrative && (
            <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 shadow-sm">
              <h4 className="text-sm font-semibold text-indigo-800">Financial Summary</h4>
              <p className="mt-2 text-sm leading-relaxed text-indigo-700">{narrative}</p>
            </div>
          )}

          {/* Working capital gap alert */}
          {wcGap?.exists && (
            <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
              <h4 className="text-sm font-semibold text-orange-800">Working Capital Gap</h4>
              <p className="mt-1 text-sm text-orange-700">
                A gap of {'\u20B9'}{fmt(wcGap.amount)} exists during months {wcGap.months.join(', ')}.
                Arrange bridge funding or phase your deployment.
              </p>
            </div>
          )}

          {/* Warnings */}
          {warnings && warnings.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
              <h4 className="text-sm font-semibold text-amber-800">Warnings</h4>
              <ul className="mt-2 space-y-1 text-sm text-amber-700">
                {warnings.map((w, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="shrink-0">{'\u26A0\uFE0F'}</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Data quality badge */}
          {dq && (
            <DataQualityBadge quality={dq.overall_quality} note={dq.lowest_confidence_assumption} />
          )}

          {/* ROI chart */}
          {roiChartData.length > 0 && (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">ROI by Scenario</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={roiChartData} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="scenario" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${fmt(v)}`} />
                  <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}`} />
                  <Legend />
                  <Bar dataKey="revenue" name="Revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="cost" name="Cost" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="profit" name="Profit" radius={[4, 4, 0, 0]}>
                    {roiChartData.map((entry: { profit?: number }, index: number) => (
                      <Cell key={index} fill={(entry.profit ?? 0) >= 0 ? '#3b82f6' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Empty state */}
          {roiChartData.length === 0 && cost_breakdown.length === 0 && (
            <EmptyState message="No economic data available for the selected crops." />
          )}
        </div>
      )}

      {/* ── COSTS ────────────────────────────────────────────────── */}
      {section === 'costs' && (
        <div className="space-y-6">
          {/* Cost composition pie */}
          {costComposition.length > 0 && (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">Cost Composition</h3>
              <div className="flex items-center justify-center gap-8">
                <ResponsiveContainer width={200} height={200}>
                  <PieChart>
                    <Pie
                      data={costComposition}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    >
                      {costComposition.map((_: unknown, i: number) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}`} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 text-sm">
                  <p><span className="inline-block h-3 w-3 rounded bg-indigo-500 mr-2" />CAPEX: {`\u20B9${fmt(total_capex)}`}</p>
                  <p><span className="inline-block h-3 w-3 rounded bg-violet-400 mr-2" />OPEX: {`\u20B9${fmt(total_opex)}`}</p>
                </div>
              </div>
            </div>
          )}

          {/* Cost per crop bar chart */}
          {costChartData.length > 0 && (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">Cost per Acre by Crop</h3>
              <ResponsiveContainer width="100%" height={Math.max(200, costChartData.length * 50)}>
                <BarChart data={costChartData} layout="vertical" barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `${fmt(v)}`} />
                  <YAxis dataKey="crop_name" type="category" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}/acre`} />
                  <Legend />
                  <Bar dataKey="capex" name="CAPEX" stackId="cost" fill="#6366f1" />
                  <Bar dataKey="opex" name="OPEX" stackId="cost" fill="#a5b4fc" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Cost breakdown table with components */}
          {cost_breakdown.length > 0 && (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">Detailed Cost Breakdown</h3>
              {cost_breakdown.map((cb) => (
                <details key={cb.crop_id} className="mb-3 rounded-lg border border-surface-100">
                  <summary className="cursor-pointer p-3 text-sm font-medium text-slate-700 hover:bg-surface-50">
                    {cb.crop_name} — CAPEX {`\u20B9${fmt(cb.capex_per_acre)}`}/acre, OPEX {`\u20B9${fmt(cb.opex_per_acre)}`}/acre
                  </summary>
                  <div className="border-t border-surface-100 p-3">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b text-left text-slate-500">
                          <th className="pb-1 pr-3">Component</th>
                          <th className="pb-1 pr-3">Type</th>
                          <th className="pb-1 text-right">Avg INR/acre</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cb.components.map((comp: { component: string; cost_type: string; avg_inr_per_acre: number }, i: number) => (
                          <tr key={i} className="border-b border-surface-50">
                            <td className="py-1 pr-3 text-slate-700">{comp.component.replace(/_/g, ' ')}</td>
                            <td className="py-1 pr-3">
                              <span className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                                comp.cost_type === 'CAPEX' ? 'bg-indigo-100 text-indigo-700' :
                                comp.cost_type === 'OPEX' ? 'bg-violet-100 text-violet-700' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                                {comp.cost_type}
                              </span>
                            </td>
                            <td className="py-1 text-right font-mono text-slate-700">{`\u20B9${fmt(comp.avg_inr_per_acre)}`}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              ))}
            </div>
          )}

          {cost_breakdown.length === 0 && (
            <EmptyState message="No cost data available for the selected crops." />
          )}
        </div>
      )}

      {/* ── REVENUE & ROI ────────────────────────────────────────── */}
      {section === 'revenue' && (
        <div className="space-y-6">
          {/* Revenue summary cards */}
          {revenue_summary && (
            <div className="grid gap-3 sm:grid-cols-3">
              <ScenarioCard
                label="Optimistic"
                revenue={revenue_summary.best_total}
                profit={profit_summary?.best}
                breakeven={break_even?.best_months as number | null | undefined}
                annualizedRoi={bestScenario?.annualized_roi_pct}
                capitalRequired={bestScenario?.capital_required}
                paybackStatus={bestScenario?.payback_status}
                color="green"
              />
              <ScenarioCard
                label="Base Case"
                revenue={revenue_summary.base_total}
                profit={profit_summary?.base}
                breakeven={break_even?.base_months as number | null | undefined}
                annualizedRoi={baseScenario?.annualized_roi_pct}
                capitalRequired={baseScenario?.capital_required}
                paybackStatus={baseScenario?.payback_status}
                color="blue"
              />
              <ScenarioCard
                label="Conservative"
                revenue={revenue_summary.worst_total}
                profit={profit_summary?.worst}
                breakeven={break_even?.worst_months as number | null | undefined}
                annualizedRoi={worstScenario?.annualized_roi_pct}
                capitalRequired={worstScenario?.capital_required}
                paybackStatus={worstScenario?.payback_status}
                color="red"
              />
            </div>
          )}

          {/* ROI comparison table */}
          {roi_summary.length > 0 && (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">Scenario Comparison</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface-200 text-left text-slate-600">
                      <th className="pb-2 pr-4">Scenario</th>
                      <th className="pb-2 pr-4 text-right">Revenue</th>
                      <th className="pb-2 pr-4 text-right">Cost</th>
                      <th className="pb-2 pr-4 text-right">Profit</th>
                      <th className="pb-2 pr-4 text-right">ROI %</th>
                      <th className="pb-2 pr-4 text-right">Capital Required</th>
                      <th className="pb-2 text-right">Break-even</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roi_summary.map((r) => (
                      <tr key={r.scenario} className="border-b border-surface-100">
                        <td className="py-2 pr-4">
                          <span
                            className="inline-block h-2 w-2 rounded-full mr-2"
                            style={{ backgroundColor: SCENARIO_COLORS[r.scenario] || '#94a3b8' }}
                          />
                          {r.scenario.charAt(0).toUpperCase() + r.scenario.slice(1)}
                        </td>
                        <td className="py-2 pr-4 text-right font-mono">{`\u20B9${fmt(r.revenue)}`}</td>
                        <td className="py-2 pr-4 text-right font-mono">{`\u20B9${fmt(r.total_cost)}`}</td>
                        <td className={`py-2 pr-4 text-right font-mono font-medium ${r.profit >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                          {`\u20B9${fmt(r.profit)}`}
                        </td>
                        <td className={`py-2 pr-4 text-right font-medium ${r.roi_pct >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                          {r.roi_pct.toFixed(1)}%
                        </td>
                        <td className="py-2 pr-4 text-right font-mono">{`\u20B9${fmt(r.capital_required)}`}</td>
                        <td className="py-2 text-right">
                          {formatPayback(r.breakeven_months, r.payback_status)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {roi_summary.length === 0 && (
            <EmptyState message="No revenue data available. Yield or price data may be missing." />
          )}
        </div>
      )}

      {/* ── MONTHLY CASHFLOW ───────────────────────────────────────── */}
      {section === 'cashflow' && (
        <div className="space-y-6">
          {cashflow.length > 0 ? (
            <>
              {/* Cashflow chart */}
              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Year 1 Monthly Cashflow</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={cashflow.map((mc) => ({
                      month: `M${mc.month}`,
                      Revenue: mc.revenue,
                      Expense: -mc.operating_expense,
                      net: mc.net_cash,
                    }))}
                    barGap={2}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${fmt(Math.abs(v))}`} />
                    <Tooltip formatter={(value) => `\u20B9${fmt(Math.abs(Number(value)))}`} />
                    <Legend />
                    <Bar dataKey="Revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Cumulative position line chart */}
              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Cumulative Cash Position</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart
                    data={cashflow.map((mc) => ({
                      month: `M${mc.month}`,
                      cumulative: mc.cumulative_position,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${fmt(v)}`} />
                    <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}`} />
                    <Line
                      type="monotone"
                      dataKey="cumulative"
                      name="Cumulative Position"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={{ fill: '#6366f1', r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Working capital gap */}
              {wcGap?.exists && (
                <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
                  <h4 className="text-sm font-semibold text-orange-800">Working Capital Gap</h4>
                  <div className="mt-2 grid gap-3 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-orange-600">Gap Amount</p>
                      <p className="text-lg font-bold text-orange-800">{'\u20B9'}{fmt(wcGap.amount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-orange-600">Negative Months</p>
                      <p className="text-lg font-bold text-orange-800">{wcGap.months.map((m) => `M${m}`).join(', ')}</p>
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-orange-600">
                    This is the funding you need to arrange before revenue starts flowing.
                    Consider phased deployment or a short-term working capital loan.
                  </p>
                </div>
              )}

              {/* Cashflow table */}
              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Monthly Breakdown</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-200 text-left text-slate-600">
                        <th className="pb-2 pr-4">Month</th>
                        <th className="pb-2 pr-4 text-right">Expense</th>
                        <th className="pb-2 pr-4 text-right">Revenue</th>
                        <th className="pb-2 pr-4 text-right">Net Cash</th>
                        <th className="pb-2 text-right">Cumulative</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cashflow.map((mc) => (
                        <tr key={mc.month} className="border-b border-surface-100">
                          <td className="py-2 pr-4 font-medium text-slate-700">Month {mc.month}</td>
                          <td className="py-2 pr-4 text-right font-mono text-red-600">{`\u20B9${fmt(mc.operating_expense)}`}</td>
                          <td className="py-2 pr-4 text-right font-mono text-green-700">{`\u20B9${fmt(mc.revenue)}`}</td>
                          <td className={`py-2 pr-4 text-right font-mono font-medium ${mc.net_cash >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {`\u20B9${fmt(mc.net_cash)}`}
                          </td>
                          <td className={`py-2 text-right font-mono font-medium ${mc.cumulative_position >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {`\u20B9${fmt(mc.cumulative_position)}`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <EmptyState message="Monthly cashflow data is not available." />
          )}
        </div>
      )}

      {/* ── SENSITIVITY ──────────────────────────────────────────── */}
      {section === 'sensitivity' && (
        <div className="space-y-6">
          {sensitivity.length > 0 ? (
            <>
              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Sensitivity Analysis</h3>
                <ResponsiveContainer width="100%" height={Math.max(200, sensitivity.length * 40)}>
                  <BarChart
                    data={sensitivity.map((s) => ({
                      factor: s.factor.replace(/_/g, ' '),
                      roi: s.adjusted_roi_pct,
                      profitable: s.still_profitable,
                    }))}
                    layout="vertical"
                    barGap={2}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
                    <YAxis dataKey="factor" type="category" width={130} tick={{ fontSize: 10 }} />
                    <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                    <Bar dataKey="roi" name="Adjusted ROI" radius={[0, 4, 4, 0]}>
                      {sensitivity.map((s, i) => (
                        <Cell key={i} fill={s.still_profitable ? '#22c55e' : '#ef4444'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Scenario Details</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-200 text-left text-slate-600">
                        <th className="pb-2 pr-4">Factor</th>
                        <th className="pb-2 pr-4">Description</th>
                        <th className="pb-2 pr-4 text-right">Adj. Revenue</th>
                        <th className="pb-2 pr-4 text-right">Adj. Profit</th>
                        <th className="pb-2 pr-4 text-right">Adj. ROI</th>
                        <th className="pb-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sensitivity.map((s) => (
                        <tr key={s.factor} className="border-b border-surface-100">
                          <td className="py-2 pr-4 font-medium text-slate-700">{s.factor.replace(/_/g, ' ')}</td>
                          <td className="py-2 pr-4 text-xs text-slate-500">{s.description}</td>
                          <td className="py-2 pr-4 text-right font-mono text-xs">{`\u20B9${fmt(s.adjusted_revenue)}`}</td>
                          <td className={`py-2 pr-4 text-right font-mono text-xs font-medium ${s.adjusted_profit >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {`\u20B9${fmt(s.adjusted_profit)}`}
                          </td>
                          <td className={`py-2 pr-4 text-right font-mono font-medium ${s.adjusted_roi_pct >= 0 ? 'text-green-700' : 'text-red-600'}`}>
                            {s.adjusted_roi_pct.toFixed(1)}%
                          </td>
                          <td className="py-2">
                            {s.still_profitable ? (
                              <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                                Profitable
                              </span>
                            ) : (
                              <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                                Loss
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <EmptyState message="No sensitivity analysis available. Base revenue data may be missing." />
          )}
        </div>
      )}

      {/* ── DATA QUALITY ───────────────────────────────────────────── */}
      {section === 'data_quality' && (
        <div className="space-y-6">
          {dq ? (
            <>
              {/* Overall quality badge */}
              <DataQualityBadge quality={dq.overall_quality} note={dq.lowest_confidence_assumption} large />

              {/* Data provenance */}
              <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-base font-semibold text-slate-800">Data Provenance</h3>
                <div className="space-y-4">
                  {dq.fields_from_live_fetch.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">Live Fetch</span>
                        <span className="text-xs text-slate-500">{dq.fields_from_live_fetch.length} field(s)</span>
                      </div>
                      <ul className="ml-4 text-sm text-slate-600">
                        {dq.fields_from_live_fetch.map((f, i) => (
                          <li key={i} className="flex gap-1.5 py-0.5">
                            <span className="text-green-500">{'\u2713'}</span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {dq.fields_from_database.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">Database</span>
                        <span className="text-xs text-slate-500">{dq.fields_from_database.length} field(s)</span>
                      </div>
                      <ul className="ml-4 text-sm text-slate-600">
                        {dq.fields_from_database.map((f, i) => (
                          <li key={i} className="flex gap-1.5 py-0.5">
                            <span className="text-blue-500">{'\u2713'}</span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {dq.fields_from_fallback.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">Fallback</span>
                        <span className="text-xs text-slate-500">{dq.fields_from_fallback.length} field(s)</span>
                      </div>
                      <ul className="ml-4 text-sm text-slate-600">
                        {dq.fields_from_fallback.map((f, i) => (
                          <li key={i} className="flex gap-1.5 py-0.5">
                            <span className="text-red-500">{'\u26A0'}</span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Price sources table */}
              {priceSources.length > 0 && (
                <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                  <h3 className="mb-4 text-base font-semibold text-slate-800">Price Sources</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-surface-200 text-left text-slate-600">
                          <th className="pb-2 pr-4">Crop</th>
                          <th className="pb-2 pr-4">Source</th>
                          <th className="pb-2 pr-4">Confidence</th>
                          <th className="pb-2 pr-4 text-right">Price Min</th>
                          <th className="pb-2 pr-4 text-right">Price Max</th>
                          <th className="pb-2">Fetch Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {priceSources.map((ps, i) => {
                          const conf = QUALITY_COLORS[ps.confidence] || QUALITY_COLORS.LOW
                          return (
                            <tr key={i} className="border-b border-surface-100">
                              <td className="py-2 pr-4 font-medium text-slate-700">{ps.crop}</td>
                              <td className="py-2 pr-4 text-xs text-slate-500">{ps.source}</td>
                              <td className="py-2 pr-4">
                                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${conf.badge}`}>
                                  {ps.confidence}
                                </span>
                              </td>
                              <td className="py-2 pr-4 text-right font-mono text-xs">
                                {ps.price_min != null ? `\u20B9${fmt(ps.price_min)}` : '\u2014'}
                              </td>
                              <td className="py-2 pr-4 text-right font-mono text-xs">
                                {ps.price_max != null ? `\u20B9${fmt(ps.price_max)}` : '\u2014'}
                              </td>
                              <td className="py-2 text-xs text-slate-500">{ps.fetch_date}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <EmptyState message="Data quality information is not available." />
          )}

          {/* Data coverage bar */}
          <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700">Data Coverage</span>
              <span className="text-sm font-bold text-slate-800">{Math.round(data_coverage * 100)}%</span>
            </div>
            <div className="mt-2 h-2 w-full rounded-full bg-surface-100">
              <div
                className={`h-2 rounded-full ${data_coverage >= 0.8 ? 'bg-green-500' : data_coverage >= 0.5 ? 'bg-amber-500' : 'bg-red-500'}`}
                style={{ width: `${Math.round(data_coverage * 100)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {data_coverage >= 0.8 ? 'Good coverage — most crops have detailed cost data.' :
               data_coverage >= 0.5 ? 'Moderate coverage — some crops use practice-level estimates.' :
               'Low coverage — many crops use practice-level estimates. Results are approximate.'}
            </p>
          </div>
        </div>
      )}

      {/* ── ASSUMPTIONS ──────────────────────────────────────────── */}
      {section === 'assumptions' && (
        <div className="space-y-6">
          {assumptions_used && assumptions_used.length > 0 ? (
            <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-base font-semibold text-slate-800">Assumptions Used</h3>
              <ul className="space-y-1.5 text-sm text-slate-600">
                {assumptions_used.map((a, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="shrink-0 text-slate-400">{'\u2022'}</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState message="No assumptions data available." />
          )}
        </div>
      )}
    </div>
  )
}

/* ── Helper components ──────────────────────────────────────────────── */

function SummaryCard({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 text-center shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-bold text-slate-800">
        {unit === 'INR' ? `\u20B9${fmt(value)}` : unit === '%' ? `${value}%` : fmt(value)}
      </p>
    </div>
  )
}

function ScenarioCard({
  label, revenue, profit, breakeven, annualizedRoi, capitalRequired, paybackStatus, color,
}: {
  label: string
  revenue: number
  profit: number | undefined
  breakeven: number | null | undefined
  annualizedRoi?: number
  capitalRequired?: number
  paybackStatus?: string
  color: string
}) {
  const borderColor = color === 'green' ? 'border-green-200' : color === 'red' ? 'border-red-200' : 'border-blue-200'
  const bgColor = color === 'green' ? 'bg-green-50' : color === 'red' ? 'bg-red-50' : 'bg-blue-50'
  const textColor = color === 'green' ? 'text-green-800' : color === 'red' ? 'text-red-800' : 'text-blue-800'

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-4 shadow-sm`}>
      <p className={`text-xs font-semibold uppercase tracking-wide ${textColor}`}>{label}</p>
      <div className="mt-2 space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-600">Revenue</span>
          <span className="font-mono font-medium">{`\u20B9${fmt(revenue)}`}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Profit</span>
          <span className={`font-mono font-medium ${(profit ?? 0) >= 0 ? 'text-green-700' : 'text-red-600'}`}>
            {`\u20B9${fmt(profit ?? 0)}`}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Annualized ROI</span>
          <span className={`font-mono font-medium ${(annualizedRoi ?? 0) >= 0 ? 'text-green-700' : 'text-red-600'}`}>
            {annualizedRoi != null ? `${annualizedRoi.toFixed(1)}%` : '\u2014'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Capital Need</span>
          <span className="font-mono">{capitalRequired != null ? `\u20B9${fmt(capitalRequired)}` : '\u2014'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-600">Break-even</span>
          <span className="font-mono">{formatPayback(breakeven, paybackStatus)}</span>
        </div>
      </div>
    </div>
  )
}

function DataQualityBadge({ quality, note, large }: { quality: string; note: string; large?: boolean }) {
  const colors = QUALITY_COLORS[quality] || QUALITY_COLORS.MED
  const icon = quality === 'HIGH' ? '\u2705' : quality === 'MED' ? '\u26A0\uFE0F' : '\u274C'
  const label = quality === 'HIGH' ? 'High Confidence' : quality === 'MED' ? 'Moderate Confidence' : 'Low Confidence'

  return (
    <div className={`rounded-xl border ${colors.border} ${colors.bg} ${large ? 'p-5' : 'p-3'}`}>
      <div className="flex items-center gap-2">
        <span className={large ? 'text-xl' : 'text-base'}>{icon}</span>
        <div>
          <p className={`font-semibold ${colors.text} ${large ? 'text-base' : 'text-sm'}`}>
            Data Quality: {label}
          </p>
          <p className={`${colors.text} opacity-80 ${large ? 'text-sm mt-1' : 'text-xs'}`}>{note}</p>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white p-8 text-center shadow-sm">
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  )
}
