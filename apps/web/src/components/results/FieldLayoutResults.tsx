import type { FieldLayoutPlan } from '../../types'

const BLOCK_COLORS = [
  'bg-emerald-100 border-emerald-300 text-emerald-800',
  'bg-blue-100 border-blue-300 text-blue-800',
  'bg-amber-100 border-amber-300 text-amber-800',
  'bg-purple-100 border-purple-300 text-purple-800',
  'bg-rose-100 border-rose-300 text-rose-800',
  'bg-cyan-100 border-cyan-300 text-cyan-800',
]

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

export function FieldLayoutResults({ layout }: { layout: FieldLayoutPlan }) {
  const { blocks, total_area_used_acres, notes } = layout

  return (
    <div className="space-y-6">
      {/* Visual block layout */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-800">Field Block Layout</h3>
        <p className="mb-4 text-sm text-slate-500">
          Total planned area: <strong>{total_area_used_acres} acres</strong>
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {blocks.map((block, i) => (
            <div
              key={block.block_label}
              className={`rounded-xl border-2 p-4 ${BLOCK_COLORS[i % BLOCK_COLORS.length]}`}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider opacity-60">
                  {block.block_label}
                </span>
                <span className="text-sm font-semibold">{block.area_acres} ac</span>
              </div>
              <p className="text-lg font-bold">{block.crop_name}</p>
              <div className="mt-3 space-y-1 text-xs opacity-80">
                <p>Row: {block.row_spacing_cm} cm | Plant: {block.plant_spacing_cm} cm</p>
                <p>Plants: {fmt(block.total_plants)}</p>
                {block.rows > 0 && (
                  <p>{block.rows} rows &times; {block.plants_per_row} plants/row</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed table */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-800">Spacing Details</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-200 text-left text-slate-600">
                <th className="pb-2 pr-3">Block</th>
                <th className="pb-2 pr-3">Crop</th>
                <th className="pb-2 pr-3 text-right">Area (ac)</th>
                <th className="pb-2 pr-3 text-right">Row (cm)</th>
                <th className="pb-2 pr-3 text-right">Plant (cm)</th>
                <th className="pb-2 pr-3 text-right">Total Plants</th>
                <th className="pb-2 pr-3 text-right">Rows</th>
                <th className="pb-2 text-right">Plants/Row</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((b) => (
                <tr key={b.block_label} className="border-b border-surface-100">
                  <td className="py-2 pr-3 font-medium">{b.block_label}</td>
                  <td className="py-2 pr-3">{b.crop_name}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.area_acres}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.row_spacing_cm}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.plant_spacing_cm}</td>
                  <td className="py-2 pr-3 text-right font-mono">{fmt(b.total_plants)}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.rows}</td>
                  <td className="py-2 text-right font-mono">{b.plants_per_row}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Notes */}
      {notes.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-amber-900">Layout Notes</h3>
          <ul className="list-inside list-disc text-sm text-amber-800">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
