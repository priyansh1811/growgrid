import { useState } from 'react'
import type { PlanResponse } from '../api/client'
import { OverviewDashboard } from './results/OverviewDashboard'
import { EconomicsResults } from './results/EconomicsResults'
import { FieldLayoutResults } from './results/FieldLayoutResults'
import { SchemesResults } from './results/SchemesResults'
import { CriticResults } from './results/CriticResults'
import { IcarAdvisoryResults } from './results/IcarAdvisoryResults'

interface PlanResultsProps {
  plan: PlanResponse
  onBack: () => void
}

type TabKey = 'overview' | 'practice' | 'crops' | 'economics' | 'layout' | 'icar' | 'schemes' | 'review' | 'guides'

interface Tab {
  key: TabKey
  label: string
  available: boolean
}

export function PlanResults({ plan, onBack }: PlanResultsProps) {
  const {
    goal_weights, selected_practice, selected_crop_portfolio,
    agronomist_verification, grow_guides,
  } = plan
  const weights = goal_weights || {}

  const tabs: Tab[] = [
    { key: 'overview', label: 'Overview', available: true },
    { key: 'practice', label: 'Practice', available: true },
    { key: 'crops', label: 'Crops', available: true },
    { key: 'economics', label: 'Economics', available: !!plan.economics },
    { key: 'layout', label: 'Layout', available: !!plan.field_layout },
    { key: 'icar', label: 'ICAR Advisory', available: !!plan.icar_advisory },
    { key: 'schemes', label: 'Schemes', available: !!plan.schemes },
    { key: 'review', label: 'Review', available: !!plan.critic_report || !!agronomist_verification },
    { key: 'guides', label: 'Grow Guides', available: grow_guides && grow_guides.length > 0 },
  ]

  const availableTabs = tabs.filter((t) => t.available)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">Your Farm Plan</h1>
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg border border-surface-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-surface-50"
        >
          New Plan
        </button>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-surface-200">
        <nav className="-mb-px flex gap-1 overflow-x-auto" aria-label="Plan sections">
          {availableTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-slate-500 hover:border-surface-300 hover:text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="min-h-[300px]">
        {activeTab === 'overview' && <OverviewDashboard plan={plan} />}

        {activeTab === 'practice' && (
          <div className="space-y-6">
            <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Recommended Practice</h2>
              {selected_practice.eliminated ? (
                <p className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
                  No feasible practice found. {selected_practice.elimination_reason}
                </p>
              ) : (
                <>
                  <p className="rounded-lg bg-primary-50 p-3 text-primary-800">
                    <strong>{selected_practice.practice_name}</strong> (score: {selected_practice.weighted_score.toFixed(3)})
                  </p>
                  {plan.selected_practice_reason && (
                    <p className="mt-3 text-sm text-slate-600">{plan.selected_practice_reason}</p>
                  )}
                  {selected_practice.fit_scores && Object.keys(selected_practice.fit_scores).length > 0 && (
                    <details className="mt-3">
                      <summary className="cursor-pointer text-sm text-primary-600">Score breakdown</summary>
                      <ul className="mt-2 space-y-1 text-sm text-slate-600">
                        {Object.entries(selected_practice.fit_scores).map(([dim, val]) => (
                          <li key={dim}>
                            {dim}: {(val as number).toFixed(2)} &times; weight = {((val as number) * (weights[dim] ?? 0)).toFixed(3)}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </>
              )}
            </section>

            {/* Alternatives */}
            {plan.practice_alternatives && plan.practice_alternatives.length > 0 && (
              <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold text-slate-800">Alternative Practices</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-200 text-left text-slate-600">
                        <th className="pb-2 pr-4">Practice</th>
                        <th className="pb-2 text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.practice_alternatives.map((alt) => (
                        <tr key={alt.practice_code} className="border-b border-surface-100">
                          <td className="py-2 pr-4">{alt.practice_name}</td>
                          <td className="py-2 text-right font-mono">{alt.weighted_score.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Constraints */}
            <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Constraints Applied</h2>
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
        )}

        {activeTab === 'crops' && (
          <div className="space-y-6">
            <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Crop Portfolio</h2>
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
                        <th className="pb-2 pr-4 text-right">Area</th>
                        <th className="pb-2 pr-4">Role</th>
                        <th className="pb-2 text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected_crop_portfolio.map((entry, i) => (
                        <tr key={i} className="border-b border-surface-100">
                          <td className="py-2 pr-4 font-medium">{entry.crop_name}</td>
                          <td className="py-2 pr-4 text-right font-mono">{(entry.area_fraction * 100).toFixed(0)}%</td>
                          <td className="py-2 pr-4 text-slate-500">{entry.role_hint}</td>
                          <td className="py-2 text-right font-mono">{entry.score.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        )}

        {activeTab === 'economics' && plan.economics && (
          <EconomicsResults economics={plan.economics} economistOutput={plan.economist_output} />
        )}

        {activeTab === 'layout' && plan.field_layout && (
          <FieldLayoutResults layout={plan.field_layout} />
        )}

        {activeTab === 'icar' && plan.icar_advisory && (
          <IcarAdvisoryResults advisory={plan.icar_advisory} />
        )}

        {activeTab === 'schemes' && plan.schemes && (
          <SchemesResults schemes={plan.schemes} />
        )}

        {activeTab === 'review' && (
          <div className="space-y-6">
            {/* Critic report */}
            {plan.critic_report && (
              <div>
                <h2 className="mb-4 text-lg font-semibold text-slate-800">Consistency Review</h2>
                <CriticResults critic={plan.critic_report} />
              </div>
            )}

            {/* Agronomist verification */}
            <section className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Agronomist Verification</h2>
              <p className="mb-3 text-sm">
                Confidence: <strong>{(agronomist_verification.confidence_score * 100).toFixed(0)}%</strong>
                {agronomist_verification.confidence_score >= 0.8 && ' \u2014 High confidence'}
                {agronomist_verification.confidence_score >= 0.5 && agronomist_verification.confidence_score < 0.8 && ' \u2014 Moderate confidence'}
                {agronomist_verification.confidence_score < 0.5 && ' \u2014 Low confidence; manual review recommended'}
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
          </div>
        )}

        {activeTab === 'guides' && grow_guides && grow_guides.length > 0 && (
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-slate-800">Grow Guides</h2>
            {grow_guides.map((guide, i) => (
              <details key={i} className="rounded-xl border border-surface-200 bg-white shadow-sm">
                <summary className="cursor-pointer p-5 font-medium text-slate-800 hover:bg-surface-50">
                  {guide.crop_name}
                </summary>
                <div className="space-y-3 border-t border-surface-200 p-5 text-sm">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="font-semibold text-slate-700">Sowing Window</p>
                      <p className="text-slate-600">{guide.sowing_window}</p>
                    </div>
                    <div>
                      <p className="font-semibold text-slate-700">Land Preparation</p>
                      <p className="text-slate-600">{guide.land_prep}</p>
                    </div>
                    <div>
                      <p className="font-semibold text-slate-700">Irrigation</p>
                      <p className="text-slate-600">{guide.irrigation_rules}</p>
                    </div>
                    <div>
                      <p className="font-semibold text-slate-700">Fertilizer Plan</p>
                      <p className="text-slate-600">{guide.fertilizer_plan}</p>
                    </div>
                  </div>

                  {guide.monthly_timeline && guide.monthly_timeline.length > 0 && (
                    <div>
                      <p className="font-semibold text-slate-700">Monthly Timeline</p>
                      <ol className="mt-1 list-inside list-decimal text-slate-600">
                        {guide.monthly_timeline.map((step, j) => (
                          <li key={j}>{step}</li>
                        ))}
                      </ol>
                    </div>
                  )}

                  {guide.pest_prevention && guide.pest_prevention.length > 0 && (
                    <div>
                      <p className="font-semibold text-slate-700">Pest Prevention</p>
                      <ul className="mt-1 list-inside list-disc text-slate-600">
                        {guide.pest_prevention.map((p, j) => (
                          <li key={j}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <p className="font-semibold text-slate-700">Harvest Notes</p>
                    <p className="text-slate-600">{guide.harvest_notes}</p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-lg bg-primary-50 p-3">
                      <p className="text-xs font-semibold text-primary-700">Why Recommended</p>
                      <p className="mt-1 text-sm text-primary-800">{guide.why_recommended}</p>
                    </div>
                    <div className="rounded-lg bg-amber-50 p-3">
                      <p className="text-xs font-semibold text-amber-700">Not Recommended When</p>
                      <p className="mt-1 text-sm text-amber-800">{guide.when_not_recommended}</p>
                    </div>
                  </div>
                </div>
              </details>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
