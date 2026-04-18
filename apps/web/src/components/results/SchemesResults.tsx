import { useState } from 'react'
import type { MatchedScheme, SchemesReport } from '../../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

/** Scheme type → display info */
const SCHEME_TYPE_META: Record<string, { label: string; icon: string; color: string }> = {
  SUBSIDY: { label: 'Subsidies & Grants', icon: '💰', color: 'emerald' },
  CREDIT: { label: 'Credit & Loans', icon: '🏦', color: 'blue' },
  INSURANCE: { label: 'Insurance', icon: '🛡️', color: 'violet' },
  INCOME_SUPPORT: { label: 'Income Support', icon: '🤝', color: 'amber' },
  MARKET: { label: 'Market Access', icon: '🏪', color: 'orange' },
  INFRASTRUCTURE: { label: 'Infrastructure & Technology', icon: '🔧', color: 'slate' },
  OTHER: { label: 'Other Schemes', icon: '📋', color: 'gray' },
}

/** Order for scheme type sections */
const TYPE_ORDER = ['SUBSIDY', 'INCOME_SUPPORT', 'CREDIT', 'INSURANCE', 'INFRASTRUCTURE', 'MARKET', 'OTHER']

function StateCentralBadge({ scheme }: { scheme: MatchedScheme }) {
  // Infer from match_reasons — state-specific schemes have state name in reasons
  const isStateSpecific = scheme.match_reasons.some(
    (r) => r.includes('State-specific') || (r.startsWith('Applicable in') && !r.includes('all states'))
  )

  if (isStateSpecific) {
    const stateMatch = scheme.match_reasons.find((r) => r.startsWith('Applicable in'))
    const stateName = stateMatch?.replace('Applicable in ', '') || 'State'
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
        <span className="text-[10px]">📍</span> {stateName} Scheme
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
      <span className="text-[10px]">🇮🇳</span> Central Scheme
    </span>
  )
}

function SchemeChecklist({ items }: { items: string[] }) {
  const [isOpen, setIsOpen] = useState(false)

  if (!items || items.length === 0) return null

  return (
    <div className="mt-3 border-t border-surface-100 pt-3">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-1.5 text-left text-sm font-medium text-slate-700 hover:text-slate-900"
      >
        <svg
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Steps to Apply
      </button>
      {isOpen && (
        <ul className="mt-2 space-y-1.5 pl-5">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-600">
              <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary-400" />
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SchemeCard({ scheme }: { scheme: MatchedScheme }) {
  return (
    <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex-1">
          <h3 className="text-base font-semibold text-slate-800">{scheme.scheme_name}</h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400">{scheme.scheme_id}</span>
            <StateCentralBadge scheme={scheme} />
            {scheme.scheme_type && scheme.scheme_type !== 'OTHER' && (
              <span className="inline-flex items-center rounded-full bg-surface-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                {SCHEME_TYPE_META[scheme.scheme_type]?.label || scheme.scheme_type}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {scheme.subsidy_pct != null && scheme.subsidy_pct > 0 && (
            <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
              {scheme.subsidy_pct}% subsidy
            </span>
          )}
          <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-xs font-medium text-slate-600">
            Score: {scheme.relevance_score}
          </span>
        </div>
      </div>

      {/* Max subsidy */}
      {scheme.max_subsidy_inr != null && scheme.max_subsidy_inr > 0 && (
        <p className="mt-2 text-sm text-slate-600">
          Max subsidy: <strong className="text-green-700">{`\u20B9${fmt(scheme.max_subsidy_inr)}`}</strong>
        </p>
      )}

      {/* Eligibility summary */}
      {scheme.eligibility_summary && (
        <p className="mt-2 text-sm text-slate-600">{scheme.eligibility_summary}</p>
      )}

      {/* Category subsidy callout */}
      {scheme.category_subsidy_note && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5">
          <p className="text-xs font-medium text-amber-800">
            <span className="mr-1">⭐</span>
            {scheme.category_subsidy_note}
          </p>
        </div>
      )}

      {/* Match reasons */}
      {scheme.match_reasons.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {scheme.match_reasons.map((reason, i) => (
            <span
              key={i}
              className="inline-flex items-center rounded-md bg-primary-50 px-2 py-0.5 text-xs text-primary-700"
            >
              {reason}
            </span>
          ))}
        </div>
      )}

      {/* Action links */}
      <div className="mt-3 flex flex-wrap items-center gap-4">
        {scheme.application_url && (
          <a
            href={scheme.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Apply online
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        )}
        {scheme.source_url && (
          <a
            href={scheme.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
          >
            Verify at source →
          </a>
        )}
      </div>

      {/* Per-scheme checklist */}
      <SchemeChecklist items={scheme.checklist_items || []} />
    </div>
  )
}

function SchemeTypeSection({
  typeCode,
  schemes,
}: {
  typeCode: string
  schemes: MatchedScheme[]
}) {
  const meta = SCHEME_TYPE_META[typeCode] || SCHEME_TYPE_META.OTHER

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <span className="text-lg">{meta.icon}</span>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {meta.label}
        </h3>
        <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-slate-500">
          {schemes.length}
        </span>
      </div>
      <div className="space-y-4">
        {schemes.map((scheme) => (
          <SchemeCard key={scheme.scheme_id} scheme={scheme} />
        ))}
      </div>
    </div>
  )
}

export function SchemesResults({ schemes }: { schemes: SchemesReport }) {
  const {
    matched_schemes,
    total_potential_subsidy,
    eligibility_checklist,
    data_note,
    schemes_by_type,
    state_specific_count,
    central_count,
  } = schemes

  // Group schemes by type for display
  const groupedSchemes: Map<string, MatchedScheme[]> = new Map()

  if (schemes_by_type && Object.keys(schemes_by_type).length > 0) {
    // Use backend grouping — but resolve to full scheme objects
    const schemeMap = new Map(matched_schemes.map((s) => [s.scheme_id, s]))
    for (const typeCode of TYPE_ORDER) {
      const ids = schemes_by_type[typeCode]
      if (!ids || ids.length === 0) continue
      const resolved = ids.map((id) => schemeMap.get(id)).filter(Boolean) as MatchedScheme[]
      if (resolved.length > 0) {
        groupedSchemes.set(typeCode, resolved)
      }
    }
    // Catch any types not in TYPE_ORDER
    for (const [typeCode, ids] of Object.entries(schemes_by_type)) {
      if (groupedSchemes.has(typeCode)) continue
      const resolved = ids.map((id) => schemeMap.get(id)).filter(Boolean) as MatchedScheme[]
      if (resolved.length > 0) {
        groupedSchemes.set(typeCode, resolved)
      }
    }
  } else {
    // Fallback: group by scheme_type on each scheme
    for (const scheme of matched_schemes) {
      const type = scheme.scheme_type || 'OTHER'
      if (!groupedSchemes.has(type)) groupedSchemes.set(type, [])
      groupedSchemes.get(type)!.push(scheme)
    }
  }

  const hasGrouping = groupedSchemes.size > 1

  return (
    <div className="space-y-6">
      {/* Summary banner */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
        {total_potential_subsidy != null && total_potential_subsidy > 0 && (
          <div className="flex-1 rounded-xl border border-green-200 bg-green-50 p-4 text-center">
            <p className="text-sm font-medium text-green-700">Total Potential Subsidy</p>
            <p className="mt-1 text-2xl font-bold text-green-800">{`\u20B9${fmt(total_potential_subsidy)}`}</p>
            <p className="mt-0.5 text-xs text-green-600">Combined max across all matched schemes</p>
          </div>
        )}
        {/* Scheme count summary */}
        <div className="flex flex-1 items-center justify-center gap-6 rounded-xl border border-surface-200 bg-white p-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-slate-800">{matched_schemes.length}</p>
            <p className="text-xs text-slate-500">Schemes Matched</p>
          </div>
          {(state_specific_count != null && state_specific_count > 0) && (
            <div className="text-center">
              <p className="text-2xl font-bold text-green-700">{state_specific_count}</p>
              <p className="text-xs text-green-600">State-Specific</p>
            </div>
          )}
          {(central_count != null && central_count > 0) && (
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-700">{central_count}</p>
              <p className="text-xs text-blue-600">Central</p>
            </div>
          )}
        </div>
      </div>

      {/* Scheme cards — grouped by type if available, flat otherwise */}
      {hasGrouping ? (
        <div className="space-y-8">
          {Array.from(groupedSchemes.entries()).map(([typeCode, typeSchemes]) => (
            <SchemeTypeSection key={typeCode} typeCode={typeCode} schemes={typeSchemes} />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {matched_schemes.map((scheme) => (
            <SchemeCard key={scheme.scheme_id} scheme={scheme} />
          ))}
        </div>
      )}

      {/* Eligibility checklist */}
      {eligibility_checklist.length > 0 && (
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-slate-800">General Eligibility Checklist</h3>
          <ul className="space-y-2">
            {eligibility_checklist.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-surface-300 bg-surface-50 text-xs text-slate-400">
                  {i + 1}
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Data note */}
      {data_note && (
        <p className="text-center text-xs text-slate-400">{data_note}</p>
      )}
    </div>
  )
}
