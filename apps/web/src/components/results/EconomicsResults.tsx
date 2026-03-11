import type { EconomicsReport } from '../../types'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts'

const SCENARIO_COLORS: Record<string, string> = {
  best: '#22c55e',
  base: '#3b82f6',
  worst: '#ef4444',
}

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

export function EconomicsResults({ economics }: { economics: EconomicsReport }) {
  const { cost_breakdown, roi_summary, sensitivity, total_capex, total_opex, data_coverage } = economics

  const roiChartData = roi_summary.map((r) => ({
    scenario: r.scenario.charAt(0).toUpperCase() + r.scenario.slice(1),
    Revenue: r.revenue,
    Cost: r.total_cost,
    Profit: r.profit,
    scenarioKey: r.scenario,
  }))

  const costChartData = cost_breakdown.map((c) => ({
    name: c.crop_name,
    CAPEX: c.capex_per_acre,
    OPEX: c.opex_per_acre,
  }))

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-surface-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Total CAPEX</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{`\u20B9${fmt(total_capex)}`}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Total OPEX</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{`\u20B9${fmt(total_opex)}`}</p>
        </div>
        <div className="rounded-xl border border-surface-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Data Coverage</p>
          <p className="mt-1 text-2xl font-bold text-slate-800">{`${(data_coverage * 100).toFixed(0)}%`}</p>
        </div>
      </div>

      {/* ROI Scenarios chart */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-800">ROI by Scenario</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={roiChartData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="scenario" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${fmt(v)}`} />
            <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}`} />
            <Legend />
            <Bar dataKey="Revenue" fill="#22c55e" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Cost" fill="#94a3b8" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Profit" radius={[4, 4, 0, 0]}>
              {roiChartData.map((entry, index) => (
                <Cell key={index} fill={entry.Profit >= 0 ? '#3b82f6' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ROI Table */}
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
                  <td className="py-2 text-right">
                    {r.breakeven_months != null ? `${r.breakeven_months} mo` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost breakdown per crop */}
      {cost_breakdown.length > 0 && (
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-slate-800">Cost per Acre by Crop</h3>
          <ResponsiveContainer width="100%" height={Math.max(200, cost_breakdown.length * 45)}>
            <BarChart data={costChartData} layout="vertical" barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={(v) => `${fmt(v)}`} />
              <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(value) => `\u20B9${fmt(Number(value))}/acre`} />
              <Legend />
              <Bar dataKey="CAPEX" stackId="cost" fill="#6366f1" radius={[0, 0, 0, 0]} />
              <Bar dataKey="OPEX" stackId="cost" fill="#a5b4fc" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Sensitivity analysis */}
      {sensitivity.length > 0 && (
        <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-slate-800">Sensitivity Analysis</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 text-left text-slate-600">
                  <th className="pb-2 pr-4">Factor</th>
                  <th className="pb-2 pr-4 text-right">Adjusted ROI</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {sensitivity.map((s) => (
                  <tr key={s.factor} className="border-b border-surface-100">
                    <td className="py-2 pr-4 font-medium text-slate-700">{s.factor.replace(/_/g, ' ')}</td>
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
      )}
    </div>
  )
}
