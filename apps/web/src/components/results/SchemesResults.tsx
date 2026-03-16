import type { SchemesReport } from '../../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

export function SchemesResults({ schemes }: { schemes: SchemesReport }) {
  const { matched_schemes, total_potential_subsidy, eligibility_checklist, data_note } = schemes

  return (
    <div className="space-y-6">
      {/* Summary */}
      {total_potential_subsidy != null && total_potential_subsidy > 0 && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-5 text-center">
          <p className="text-sm font-medium text-green-700">Total Potential Subsidy</p>
          <p className="mt-1 text-3xl font-bold text-green-800">{`\u20B9${fmt(total_potential_subsidy)}`}</p>
          <p className="mt-1 text-xs text-green-600">Combined maximum across all matched schemes</p>
        </div>
      )}

      {/* Scheme cards */}
      <div className="space-y-4">
        {matched_schemes.map((scheme) => (
          <div
            key={scheme.scheme_id}
            className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex-1">
                <h3 className="text-base font-semibold text-slate-800">{scheme.scheme_name}</h3>
                <p className="mt-1 text-sm text-slate-500">ID: {scheme.scheme_id}</p>
              </div>
              <div className="flex items-center gap-2">
                {scheme.subsidy_pct != null && (
                  <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">
                    {scheme.subsidy_pct}% subsidy
                  </span>
                )}
                <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-xs font-medium text-slate-600">
                  Score: {scheme.relevance_score}
                </span>
              </div>
            </div>

            {scheme.max_subsidy_inr != null && scheme.max_subsidy_inr > 0 && (
              <p className="mt-2 text-sm text-slate-600">
                Max subsidy: <strong className="text-green-700">{`\u20B9${fmt(scheme.max_subsidy_inr)}`}</strong>
              </p>
            )}

            {scheme.eligibility_summary && (
              <p className="mt-2 text-sm text-slate-600">{scheme.eligibility_summary}</p>
            )}

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

            {scheme.application_url && (
              <a
                href={scheme.application_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                Apply online
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}
          </div>
        ))}
      </div>

      {/* Eligibility checklist */}
      {eligibility_checklist.length > 0 && (
        <div className="rounded-xl border border-surface-200 bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-base font-semibold text-slate-800">Eligibility Checklist</h3>
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
