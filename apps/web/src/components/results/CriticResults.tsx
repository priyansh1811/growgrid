import type { CriticReport } from '../../types'

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-200',
  WARNING: 'bg-amber-100 text-amber-800 border-amber-200',
  INFO: 'bg-blue-100 text-blue-800 border-blue-200',
}

const SEVERITY_ICON: Record<string, string> = {
  CRITICAL: '\u26D4',
  WARNING: '\u26A0\uFE0F',
  INFO: '\u2139\uFE0F',
}

export function CriticResults({ critic }: { critic: CriticReport }) {
  const { issues, fixes_applied, final_confidence, summary } = critic

  const criticalCount = issues.filter((i) => i.severity === 'CRITICAL').length
  const warningCount = issues.filter((i) => i.severity === 'WARNING').length
  const infoCount = issues.filter((i) => i.severity === 'INFO').length

  const confidencePct = (final_confidence * 100).toFixed(0)
  const confidenceColor =
    final_confidence >= 0.8 ? 'text-green-700' : final_confidence >= 0.5 ? 'text-amber-700' : 'text-red-700'
  const barColor =
    final_confidence >= 0.8 ? 'bg-green-500' : final_confidence >= 0.5 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="space-y-6">
      {/* Confidence meter */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-800">Consistency Confidence</h3>
            {summary && <p className="mt-1 text-sm text-slate-500">{summary}</p>}
          </div>
          <span className={`text-3xl font-bold ${confidenceColor}`}>{confidencePct}%</span>
        </div>
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-surface-200">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${Math.min(100, final_confidence * 100)}%` }}
          />
        </div>
        <div className="mt-3 flex gap-4 text-xs text-slate-500">
          {criticalCount > 0 && <span className="text-red-600">{criticalCount} critical</span>}
          {warningCount > 0 && <span className="text-amber-600">{warningCount} warnings</span>}
          {infoCount > 0 && <span className="text-blue-600">{infoCount} info</span>}
          {issues.length === 0 && <span className="text-green-600">No issues found</span>}
        </div>
      </div>

      {/* Issues list */}
      {issues.length > 0 && (
        <div className="space-y-3">
          {issues.map((issue, i) => (
            <div
              key={i}
              className={`rounded-lg border p-4 ${SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.INFO}`}
            >
              <div className="flex items-start gap-2">
                <span className="text-base">{SEVERITY_ICON[issue.severity] || ''}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase">{issue.severity}</span>
                    <span className="text-xs opacity-60">{issue.dimension}</span>
                  </div>
                  <p className="mt-1 text-sm font-medium">{issue.description}</p>
                  {issue.affected_item && (
                    <p className="mt-1 text-xs opacity-70">Affected: {issue.affected_item}</p>
                  )}
                  {issue.suggested_fix && (
                    <p className="mt-2 text-sm italic opacity-80">Fix: {issue.suggested_fix}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Fixes applied */}
      {fixes_applied.length > 0 && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-green-800">Auto-applied Fixes</h3>
          <ul className="list-inside list-disc text-sm text-green-700">
            {fixes_applied.map((fix, i) => (
              <li key={i}>{fix}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
