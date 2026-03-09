import type { PlanResponse } from '../api/client'

interface PlanResultsProps {
  plan: PlanResponse
  onBack: () => void
}

export function PlanResults({ plan, onBack }: PlanResultsProps) {
  const { goal_weights, selected_practice, selected_crop_portfolio, agronomist_verification, grow_guides } = plan
  const weights = goal_weights || {}

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">Your plan</h1>
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-surface-50"
        >
          Generate another plan
        </button>
      </div>

      {plan.warnings && plan.warnings.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="mb-2 text-sm font-semibold text-amber-900">Warnings</h2>
          <ul className="list-inside list-disc text-sm text-amber-800">
            {plan.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </section>
      )}

      {plan.conflicts && plan.conflicts.length > 0 && (
        <section className="rounded-xl border border-red-200 bg-red-50 p-4">
          <h2 className="mb-2 text-sm font-semibold text-red-900">Conflicts</h2>
          <ul className="list-inside list-disc text-sm text-red-800">
            {plan.conflicts.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">Goal weights</h2>
          <div className="space-y-2">
            {Object.entries(weights).map(([dim, w]) => (
              <div key={dim} className="flex items-center gap-3">
                <span className="w-24 text-sm text-slate-600">{dim}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-200">
                  <div
                    className="h-full rounded-full bg-primary-500"
                    style={{ width: `${Math.min(100, w * 100)}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-slate-700">{(w as number).toFixed(2)}</span>
              </div>
            ))}
          </div>
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-primary-600">Weight explanation</summary>
            <pre className="mt-2 whitespace-pre-wrap rounded bg-surface-100 p-3 text-xs text-slate-600">
              {plan.goal_explanation}
            </pre>
          </details>
        </section>

        <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">Constraints</h2>
          {plan.hard_constraints && plan.hard_constraints.length > 0 ? (
            <ul className="space-y-2 text-sm text-slate-700">
              {plan.hard_constraints.map((c, i) => (
                <li key={i}>
                  <strong>{c.dimension}:</strong> {c.reason}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-surface-500">No hard constraints triggered.</p>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Recommended practice</h2>
        {selected_practice.eliminated ? (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
            No feasible practice found. {selected_practice.elimination_reason}
          </p>
        ) : (
          <>
            <p className="rounded-lg bg-primary-50 p-3 text-primary-800">
              <strong>{selected_practice.practice_name}</strong> (score: {selected_practice.weighted_score.toFixed(3)})
            </p>
            {selected_practice.fit_scores && Object.keys(selected_practice.fit_scores).length > 0 && (
              <details className="mt-3">
                <summary className="cursor-pointer text-sm text-primary-600">Score breakdown</summary>
                <ul className="mt-2 space-y-1 text-sm text-slate-600">
                  {Object.entries(selected_practice.fit_scores).map(([dim, val]) => (
                    <li key={dim}>
                      {dim}: {(val as number).toFixed(2)} × weight = {((val as number) * (weights[dim] ?? 0)).toFixed(3)}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </section>

      <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Crop portfolio</h2>
        {plan.selected_crop_portfolio_reason && (
          <p className="mb-3 text-sm text-slate-600">{plan.selected_crop_portfolio_reason}</p>
        )}
        {!selected_crop_portfolio || selected_crop_portfolio.length === 0 ? (
          <p className="text-sm text-amber-800">No crops could be recommended with current constraints.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-200 text-left text-slate-600">
                  <th className="pb-2 pr-4">Crop</th>
                  <th className="pb-2 pr-4">Area share</th>
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2">Score</th>
                </tr>
              </thead>
              <tbody>
                {selected_crop_portfolio.map((entry, i) => (
                  <tr key={i} className="border-b border-surface-100">
                    <td className="py-2 pr-4 font-medium">{entry.crop_name}</td>
                    <td className="py-2 pr-4">{(entry.area_fraction * 100).toFixed(0)}%</td>
                    <td className="py-2 pr-4">{entry.role_hint}</td>
                    <td className="py-2">{entry.score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Agronomist verification</h2>
        <p className="mb-3 text-sm">
          Confidence: <strong>{(agronomist_verification.confidence_score * 100).toFixed(0)}%</strong>
          {agronomist_verification.confidence_score >= 0.8 && ' — High confidence'}
          {agronomist_verification.confidence_score >= 0.5 && agronomist_verification.confidence_score < 0.8 && ' — Moderate confidence'}
          {agronomist_verification.confidence_score < 0.5 && ' — Low confidence; manual review recommended'}
        </p>
        {agronomist_verification.warnings && agronomist_verification.warnings.length > 0 && (
          <ul className="mb-3 list-inside list-disc text-sm text-amber-800">
            {agronomist_verification.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        )}
        {agronomist_verification.required_actions && agronomist_verification.required_actions.length > 0 && (
          <div className="text-sm text-slate-700">
            <strong>Required actions:</strong>
            <ul className="list-inside list-disc">
              {agronomist_verification.required_actions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {grow_guides && grow_guides.length > 0 && (
        <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">Grow guides</h2>
          <div className="space-y-6">
            {grow_guides.map((guide, i) => (
              <details key={i} className="rounded-lg border border-surface-200 bg-surface-50">
                <summary className="cursor-pointer p-4 font-medium text-slate-800">
                  {guide.crop_name} — Grow guide
                </summary>
                <div className="space-y-2 border-t border-surface-200 p-4 text-sm">
                  <p><strong>Sowing window:</strong> {guide.sowing_window}</p>
                  <p><strong>Land preparation:</strong> {guide.land_prep}</p>
                  <p><strong>Irrigation:</strong> {guide.irrigation_rules}</p>
                  <p><strong>Fertilizer:</strong> {guide.fertilizer_plan}</p>
                  {guide.monthly_timeline && guide.monthly_timeline.length > 0 && (
                    <div>
                      <strong>Monthly timeline:</strong>
                      <ul className="list-inside list-disc">
                        {guide.monthly_timeline.map((step, j) => (
                          <li key={j}>{step}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {guide.pest_prevention && guide.pest_prevention.length > 0 && (
                    <div>
                      <strong>Pest prevention:</strong>
                      <ul className="list-inside list-disc">
                        {guide.pest_prevention.map((p, j) => (
                          <li key={j}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p><strong>Harvest:</strong> {guide.harvest_notes}</p>
                  <p className="rounded bg-primary-50 p-2 text-primary-800">Why recommended: {guide.why_recommended}</p>
                  <p className="rounded bg-amber-50 p-2 text-amber-800">Not recommended when: {guide.when_not_recommended}</p>
                </div>
              </details>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
