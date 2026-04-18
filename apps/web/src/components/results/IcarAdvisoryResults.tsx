import { useState } from 'react'
import type { IcarAdvisoryReport, IcarAdvisory } from '../../types'

const MONTHS: Record<number, string> = {
  1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
  7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec',
}

function MonthRangeBar({ start, end }: { start?: number | null; end?: number | null }) {
  if (!start || !end) return null
  const s = Math.max(1, Math.min(12, start))
  const e = Math.max(1, Math.min(12, end))

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 12 }, (_, i) => {
        const m = i + 1
        const inRange = s <= e ? (m >= s && m <= e) : (m >= s || m <= e)
        return (
          <div
            key={m}
            title={MONTHS[m]}
            className={`flex h-7 w-7 items-center justify-center rounded text-[10px] font-medium transition-colors ${
              inRange
                ? 'bg-emerald-500 text-white shadow-sm'
                : 'bg-surface-100 text-slate-400'
            }`}
          >
            {MONTHS[m]?.[0]}
          </div>
        )
      })}
    </div>
  )
}

type SubTab = 'calendar' | 'nutrients' | 'pests' | 'varieties' | 'weeds'

function CropAdvisoryCard({ advisory }: { advisory: IcarAdvisory }) {
  const [subTab, setSubTab] = useState<SubTab>('calendar')

  const subTabs: { key: SubTab; label: string; count: number }[] = [
    { key: 'calendar', label: 'Sowing Calendar', count: advisory.calendar.length },
    { key: 'nutrients', label: 'Nutrient Plan', count: advisory.nutrient_plans.length },
    { key: 'pests', label: 'Pest & Disease', count: advisory.pests.length },
    { key: 'varieties', label: 'Varieties', count: advisory.varieties.length },
    { key: 'weeds', label: 'Weed Mgmt', count: advisory.weed_management.length },
  ]

  const availableSubs = subTabs.filter((t) => t.count > 0)

  return (
    <div className="rounded-xl border border-surface-200 bg-white shadow-sm">
      {/* Crop header */}
      <div className="border-b border-surface-100 px-5 py-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-800">{advisory.crop_name}</h3>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              {advisory.season}
            </span>
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              ICAR Verified
            </span>
          </div>
        </div>
      </div>

      {/* Sub-tabs */}
      {availableSubs.length > 0 && (
        <>
          <div className="border-b border-surface-100 px-5">
            <nav className="-mb-px flex gap-1 overflow-x-auto" aria-label="Advisory sections">
              {availableSubs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setSubTab(tab.key)}
                  className={`whitespace-nowrap border-b-2 px-3 py-2 text-xs font-medium transition-colors ${
                    subTab === tab.key
                      ? 'border-emerald-500 text-emerald-700'
                      : 'border-transparent text-slate-400 hover:border-surface-300 hover:text-slate-600'
                  }`}
                >
                  {tab.label}
                  <span className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-surface-100 text-[10px] text-slate-500">
                    {tab.count}
                  </span>
                </button>
              ))}
            </nav>
          </div>

          <div className="p-5">
            {/* Calendar tab */}
            {subTab === 'calendar' && advisory.calendar.length > 0 && (
              <div className="space-y-4">
                {advisory.calendar.map((cal, i) => (
                  <div key={i} className="space-y-3">
                    {cal.sub_region && (
                      <p className="text-xs font-medium text-slate-500">
                        Sub-region: {cal.sub_region}
                      </p>
                    )}
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Sowing Window
                      </p>
                      <MonthRangeBar start={cal.sow_start_month} end={cal.sow_end_month} />
                      {cal.sow_start_month && cal.sow_end_month && (
                        <p className="mt-1 text-xs text-slate-500">
                          {MONTHS[cal.sow_start_month]} to {MONTHS[cal.sow_end_month]}
                        </p>
                      )}
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {cal.duration_days != null && (
                        <MetricCard label="Duration" value={`${cal.duration_days} days`} />
                      )}
                      {cal.seed_rate_kg_ha != null && (
                        <MetricCard label="Seed Rate" value={`${cal.seed_rate_kg_ha} kg/ha`} />
                      )}
                      {cal.row_spacing_cm != null && (
                        <MetricCard label="Row Spacing" value={`${cal.row_spacing_cm} cm`} />
                      )}
                      {cal.plant_spacing_cm != null && (
                        <MetricCard label="Plant Spacing" value={`${cal.plant_spacing_cm} cm`} />
                      )}
                    </div>
                    {cal.harvest_month_range && (
                      <p className="text-sm text-slate-600">
                        <span className="font-medium">Harvest:</span> {cal.harvest_month_range}
                      </p>
                    )}
                    {cal.notes && (
                      <p className="text-sm text-slate-500 italic">{cal.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Nutrient plan tab */}
            {subTab === 'nutrients' && advisory.nutrient_plans.length > 0 && (
              <div className="space-y-4">
                {advisory.nutrient_plans.map((np, i) => (
                  <div key={i} className="space-y-3">
                    {np.sub_region && (
                      <p className="text-xs font-medium text-slate-500">
                        Sub-region: {np.sub_region}
                      </p>
                    )}
                    {/* NPK bars */}
                    <div className="grid gap-3 sm:grid-cols-3">
                      <NutrientBar label="Nitrogen (N)" value={np.N_kg_ha} max={200} color="blue" />
                      <NutrientBar label="Phosphorus (P)" value={np.P_kg_ha} max={120} color="amber" />
                      <NutrientBar label="Potassium (K)" value={np.K_kg_ha} max={120} color="emerald" />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      {np.FYM_t_ha != null && np.FYM_t_ha > 0 && (
                        <MetricCard label="FYM" value={`${np.FYM_t_ha} t/ha`} />
                      )}
                      {np.zinc_sulphate_kg_ha != null && np.zinc_sulphate_kg_ha > 0 && (
                        <MetricCard label="Zinc Sulphate" value={`${np.zinc_sulphate_kg_ha} kg/ha`} />
                      )}
                    </div>
                    {np.split_schedule && (
                      <div className="rounded-lg bg-blue-50 p-3">
                        <p className="text-xs font-semibold text-blue-700">Split Schedule</p>
                        <p className="mt-1 text-sm text-blue-800">{np.split_schedule}</p>
                      </div>
                    )}
                    {np.biofertilizers && (
                      <p className="text-sm text-slate-600">
                        <span className="font-medium">Biofertilizers:</span> {np.biofertilizers}
                      </p>
                    )}
                    {np.application_notes && (
                      <p className="text-sm text-slate-500 italic">{np.application_notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Pest & Disease tab */}
            {subTab === 'pests' && advisory.pests.length > 0 && (
              <div className="space-y-2">
                {advisory.pests.map((pest, i) => (
                  <details
                    key={i}
                    className="group rounded-lg border border-surface-100 bg-surface-50 transition-colors hover:bg-white"
                  >
                    <summary className="flex cursor-pointer items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex h-5 items-center rounded px-1.5 text-[10px] font-bold uppercase ${
                            pest.type === 'disease'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}
                        >
                          {pest.type || 'pest'}
                        </span>
                        <span className="text-sm font-medium text-slate-700">
                          {pest.pest_or_disease_name}
                        </span>
                      </div>
                      {pest.monitor_start_month && pest.monitor_end_month && (
                        <span className="text-xs text-slate-400">
                          {MONTHS[pest.monitor_start_month]}–{MONTHS[pest.monitor_end_month]}
                        </span>
                      )}
                    </summary>
                    <div className="space-y-2 border-t border-surface-100 px-4 py-3 text-sm">
                      {pest.chemical_control && (
                        <div>
                          <p className="text-xs font-semibold text-slate-500">Chemical Control</p>
                          <p className="text-slate-700">{pest.chemical_control}</p>
                        </div>
                      )}
                      {pest.bio_control && (
                        <div>
                          <p className="text-xs font-semibold text-slate-500">Biological Control</p>
                          <p className="text-slate-700">{pest.bio_control}</p>
                        </div>
                      )}
                      {pest.threshold_note && (
                        <p className="text-xs text-slate-500 italic">{pest.threshold_note}</p>
                      )}
                    </div>
                  </details>
                ))}
              </div>
            )}

            {/* Varieties tab */}
            {subTab === 'varieties' && advisory.varieties.length > 0 && (
              <div className="space-y-3">
                {advisory.varieties.map((v, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-surface-100 bg-surface-50 p-4"
                  >
                    <div className="flex flex-wrap items-start gap-2">
                      {v.variety_type && (
                        <span className="inline-flex items-center rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-violet-700">
                          {v.variety_type}
                        </span>
                      )}
                      {v.duration_type && (
                        <span className="inline-flex items-center rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-sky-700">
                          {v.duration_type}
                        </span>
                      )}
                      {v.purpose && (
                        <span className="inline-flex items-center rounded-full bg-surface-200 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {v.purpose}
                        </span>
                      )}
                    </div>
                    {v.variety_names && (
                      <p className="mt-2 text-sm text-slate-700 leading-relaxed">{v.variety_names}</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Weed management tab */}
            {subTab === 'weeds' && advisory.weed_management.length > 0 && (
              <div className="space-y-4">
                {advisory.weed_management.map((weed, i) => (
                  <div key={i} className="space-y-3">
                    {weed.sub_region && (
                      <p className="text-xs font-medium text-slate-500">
                        Sub-region: {weed.sub_region}
                      </p>
                    )}
                    <div className="grid gap-3 sm:grid-cols-2">
                      {weed.pre_emergence_herbicide && (
                        <div className="rounded-lg border border-amber-100 bg-amber-50 p-3">
                          <p className="text-xs font-semibold text-amber-700">Pre-emergence</p>
                          <p className="mt-1 text-sm font-medium text-amber-900">
                            {weed.pre_emergence_herbicide}
                          </p>
                          {weed.pre_em_dose && (
                            <p className="mt-0.5 text-xs text-amber-600">Dose: {weed.pre_em_dose}</p>
                          )}
                          {weed.pre_em_timing_das && (
                            <p className="text-xs text-amber-600">Timing: {weed.pre_em_timing_das} DAS</p>
                          )}
                        </div>
                      )}
                      {weed.post_emergence_herbicide && (
                        <div className="rounded-lg border border-teal-100 bg-teal-50 p-3">
                          <p className="text-xs font-semibold text-teal-700">Post-emergence</p>
                          <p className="mt-1 text-sm font-medium text-teal-900">
                            {weed.post_emergence_herbicide}
                          </p>
                          {weed.post_em_dose && (
                            <p className="mt-0.5 text-xs text-teal-600">Dose: {weed.post_em_dose}</p>
                          )}
                          {weed.post_em_timing_das && (
                            <p className="text-xs text-teal-600">Timing: {weed.post_em_timing_das} DAS</p>
                          )}
                        </div>
                      )}
                    </div>
                    {weed.manual_weeding_schedule && (
                      <p className="text-sm text-slate-600">
                        <span className="font-medium">Manual Weeding:</span>{' '}
                        {weed.manual_weeding_schedule}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {availableSubs.length === 0 && (
        <div className="p-5 text-center text-sm text-slate-400">
          No ICAR advisory data available for this crop.
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-100 bg-surface-50 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-slate-700">{value}</p>
    </div>
  )
}

function NutrientBar({
  label,
  value,
  max,
  color,
}: {
  label: string
  value?: number | null
  max: number
  color: 'blue' | 'amber' | 'emerald'
}) {
  const v = value ?? 0
  const pct = Math.min((v / max) * 100, 100)

  const colorMap = {
    blue: { bg: 'bg-blue-500', light: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-100' },
    amber: { bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-100' },
    emerald: { bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-100' },
  }
  const c = colorMap[color]

  return (
    <div className={`rounded-lg border ${c.border} ${c.light} p-3`}>
      <div className="flex items-center justify-between">
        <p className={`text-xs font-semibold ${c.text}`}>{label}</p>
        <p className={`text-sm font-bold ${c.text}`}>{v > 0 ? `${v} kg/ha` : '-'}</p>
      </div>
      <div className="mt-2 h-1.5 w-full rounded-full bg-white/60">
        <div className={`h-1.5 rounded-full ${c.bg} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function IcarAdvisoryResults({ advisory }: { advisory: IcarAdvisoryReport }) {
  const { advisories, state, season, data_note } = advisory

  return (
    <div className="space-y-6">
      {/* Header banner */}
      <div className="rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-emerald-900">ICAR Advisory</h2>
            <p className="mt-1 text-sm text-emerald-700">
              State-specific recommendations from the Indian Council of Agricultural Research
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
              {state}
            </span>
            <span className="inline-flex items-center rounded-full bg-teal-100 px-3 py-1 text-xs font-medium text-teal-700">
              {season.charAt(0).toUpperCase() + season.slice(1)} Season
            </span>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-4 text-xs text-emerald-600">
          <span>{advisories.length} crop{advisories.length !== 1 ? 's' : ''} covered</span>
          <span>
            {advisories.reduce((n, a) => n + a.pests.length, 0)} pest/disease alerts
          </span>
          <span>
            {advisories.reduce((n, a) => n + a.varieties.length, 0)} variety recommendations
          </span>
        </div>
      </div>

      {/* Crop advisories */}
      {advisories.map((adv, i) => (
        <CropAdvisoryCard key={adv.crop_id || i} advisory={adv} />
      ))}

      {/* Data note */}
      {data_note && (
        <p className="text-center text-xs text-slate-400">{data_note}</p>
      )}
    </div>
  )
}
