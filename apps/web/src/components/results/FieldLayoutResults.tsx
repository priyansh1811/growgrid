import type { FieldBlock, FieldLayoutPlan } from '../../types'

/* ── colour palette for blocks ─────────────────────────────────────── */
const BLOCK_COLORS = [
  { bg: 'bg-emerald-100', border: 'border-emerald-400', text: 'text-emerald-800', fill: '#6ee7b7', stroke: '#059669' },
  { bg: 'bg-blue-100', border: 'border-blue-400', text: 'text-blue-800', fill: '#93c5fd', stroke: '#2563eb' },
  { bg: 'bg-amber-100', border: 'border-amber-400', text: 'text-amber-800', fill: '#fcd34d', stroke: '#d97706' },
  { bg: 'bg-purple-100', border: 'border-purple-400', text: 'text-purple-800', fill: '#c4b5fd', stroke: '#7c3aed' },
  { bg: 'bg-rose-100', border: 'border-rose-400', text: 'text-rose-800', fill: '#fda4af', stroke: '#e11d48' },
  { bg: 'bg-cyan-100', border: 'border-cyan-400', text: 'text-cyan-800', fill: '#67e8f9', stroke: '#0891b2' },
]

const fmt = (n: number) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n)

const patternLabel = (p?: string) => {
  if (!p) return '—'
  return p.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const bedLabel = (b?: string) => {
  if (!b) return '—'
  return b.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

/* ── Dimension annotation helper ───────────────────────────────────── */

function DimensionLine({
  x1, y1, x2, y2, label, color = '#64748b', offset = 0, side = 'bottom',
}: {
  x1: number; y1: number; x2: number; y2: number
  label: string; color?: string; offset?: number
  side?: 'bottom' | 'top' | 'left' | 'right'
}) {
  const tickLen = 4
  const isHorizontal = side === 'bottom' || side === 'top'
  const midX = (x1 + x2) / 2
  const midY = (y1 + y2) / 2

  return (
    <g>
      {/* Line */}
      <line x1={x1} y1={y1 + offset} x2={x2} y2={y2 + offset} stroke={color} strokeWidth={0.8} />
      {/* Ticks */}
      {isHorizontal ? (
        <>
          <line x1={x1} y1={y1 + offset - tickLen} x2={x1} y2={y1 + offset + tickLen} stroke={color} strokeWidth={0.8} />
          <line x1={x2} y1={y2 + offset - tickLen} x2={x2} y2={y2 + offset + tickLen} stroke={color} strokeWidth={0.8} />
        </>
      ) : (
        <>
          <line x1={x1 + offset - tickLen} y1={y1} x2={x1 + offset + tickLen} y2={y1} stroke={color} strokeWidth={0.8} />
          <line x1={x2 + offset - tickLen} y1={y2} x2={x2 + offset + tickLen} y2={y2} stroke={color} strokeWidth={0.8} />
        </>
      )}
      {/* Label */}
      {isHorizontal ? (
        <text
          x={midX}
          y={midY + offset + (side === 'bottom' ? 10 : -5)}
          textAnchor="middle"
          fontSize={7.5}
          fontWeight="500"
          fill={color}
        >
          {label}
        </text>
      ) : (
        <text
          x={midX + offset + (side === 'right' ? 5 : -5)}
          y={midY}
          textAnchor={side === 'right' ? 'start' : 'end'}
          fontSize={7.5}
          fontWeight="500"
          fill={color}
          dominantBaseline="middle"
        >
          {label}
        </text>
      )}
    </g>
  )
}

/* ── SVG Visual Field Map ──────────────────────────────────────────── */

function FieldMapVisualization({ blocks, pathwayWidth }: { blocks: FieldBlock[]; pathwayWidth: number }) {
  if (blocks.length === 0) return null

  const totalArea = blocks.reduce((s, b) => s + b.area_acres, 0)
  const mapWidth = 720
  const mapHeight = 520
  const padding = 60
  const compassSize = 30
  const pathwayGap = 12 // px gap between blocks representing pathways
  const topMargin = 55 // space for title
  const bottomMargin = 50 // space for legend
  const usableWidth = mapWidth - padding * 2
  const usableHeight = mapHeight - topMargin - padding - bottomMargin

  // Calculate block widths proportional to area
  const totalGaps = (blocks.length - 1) * pathwayGap
  const blockTotalWidth = usableWidth - totalGaps
  const blockWidths = blocks.map(b => Math.max(70, (b.area_acres / totalArea) * blockTotalWidth))
  const widthSum = blockWidths.reduce((s, w) => s + w, 0)
  const scale = blockTotalWidth / widthSum
  const scaledWidths = blockWidths.map(w => w * scale)

  // Pre-calculate block positions
  const blockPositions: Array<{ bx: number; bw: number }> = []
  let cx = padding
  for (let i = 0; i < blocks.length; i++) {
    blockPositions.push({ bx: cx, bw: scaledWidths[i] })
    cx += scaledWidths[i] + pathwayGap
  }

  const blockTop = topMargin + padding - 25
  const blockHeight = usableHeight

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
      <h3 className="mb-1 text-base font-semibold text-slate-800">
        Visual Field Map
      </h3>
      <p className="mb-4 text-xs text-slate-500">
        Proportional layout with labelled dimensions. All measurements are actual field values.
      </p>

      <svg
        viewBox={`0 0 ${mapWidth} ${mapHeight}`}
        className="w-full rounded-lg border border-slate-200 bg-slate-50"
        style={{ maxHeight: 500 }}
      >
        {/* Compass */}
        <g transform={`translate(${mapWidth - 45}, 35)`}>
          <circle cx={0} cy={0} r={compassSize / 2 + 4} fill="white" stroke="#94a3b8" strokeWidth={1} />
          <line x1={0} y1={-compassSize / 2} x2={0} y2={compassSize / 2} stroke="#64748b" strokeWidth={1.5} />
          <line x1={-compassSize / 2} y1={0} x2={compassSize / 2} y2={0} stroke="#cbd5e1" strokeWidth={1} />
          <polygon points={`0,${-compassSize / 2 - 2} -4,${-compassSize / 2 + 6} 4,${-compassSize / 2 + 6}`} fill="#dc2626" />
          <text x={0} y={-compassSize / 2 - 5} textAnchor="middle" fontSize={9} fontWeight="bold" fill="#dc2626">N</text>
          <text x={0} y={compassSize / 2 + 11} textAnchor="middle" fontSize={8} fill="#94a3b8">S</text>
        </g>

        {/* Title */}
        <text x={padding} y={24} fontSize={13} fontWeight="600" fill="#334155">
          Field Layout — {totalArea.toFixed(2)} acres
        </text>
        <text x={padding} y={40} fontSize={9} fill="#64748b">
          ↕ Rows run N–S for best sunlight
        </text>

        {/* Border crop strip */}
        <rect
          x={padding - 10}
          y={blockTop - 8}
          width={usableWidth + 20}
          height={blockHeight + 16}
          rx={10}
          fill="none"
          stroke="#16a34a"
          strokeWidth={1.5}
          strokeDasharray="6,4"
        />

        {/* Blocks with full labelling */}
        {blocks.map((block, i) => {
          const color = BLOCK_COLORS[i % BLOCK_COLORS.length]
          const { bx, bw } = blockPositions[i]
          const by = blockTop
          const bh = blockHeight

          // Row lines inside block
          const rowCount = Math.min(block.rows, 30)
          const rowElements = []
          if (rowCount > 1 && bw > 50) {
            const displayRows = Math.min(rowCount, 12)
            const displaySpacing = bh / (displayRows + 1)
            for (let r = 1; r <= displayRows; r++) {
              rowElements.push(
                <line
                  key={`row-${i}-${r}`}
                  x1={bx + 4}
                  y1={by + r * displaySpacing}
                  x2={bx + bw - 4}
                  y2={by + r * displaySpacing}
                  stroke={color.stroke}
                  strokeWidth={0.7}
                  strokeOpacity={0.35}
                  strokeDasharray="3,3"
                />
              )
            }

            // Plant dots on first two visible rows (to show plant spacing)
            if (block.plant_spacing_cm > 0 && bw > 70) {
              const dotsPerRow = Math.min(6, Math.floor((bw - 16) / 10))
              const dotSpacing = (bw - 16) / (dotsPerRow + 1)
              for (let row = 1; row <= Math.min(2, displayRows); row++) {
                for (let d = 1; d <= dotsPerRow; d++) {
                  rowElements.push(
                    <circle
                      key={`dot-${i}-${row}-${d}`}
                      cx={bx + 8 + d * dotSpacing}
                      cy={by + row * displaySpacing}
                      r={2}
                      fill={color.stroke}
                      fillOpacity={0.5}
                    />
                  )
                }
              }
            }
          }

          return (
            <g key={block.block_label}>
              {/* Block rectangle */}
              <rect
                x={bx} y={by} width={bw} height={bh} rx={6}
                fill={color.fill} fillOpacity={0.3}
                stroke={color.stroke} strokeWidth={2}
              />
              {/* Row lines + plant dots */}
              {rowElements}

              {/* Block label */}
              <text x={bx + bw / 2} y={by + 16} textAnchor="middle"
                fontSize={10} fontWeight="bold" fill={color.stroke}>
                {block.block_label}
              </text>
              {/* Crop name */}
              <text x={bx + bw / 2} y={by + 30} textAnchor="middle"
                fontSize={bw < 90 ? 8 : 11} fontWeight="600" fill="#1e293b">
                {block.crop_name}
              </text>
              {/* Area */}
              <text x={bx + bw / 2} y={by + 43} textAnchor="middle"
                fontSize={9} fill="#475569">
                {block.area_acres} ac
              </text>

              {/* ── Row spacing annotation (left side of block) ── */}
              {block.rows > 1 && rowCount > 1 && bw > 50 ? (() => {
                const dispRows = Math.min(rowCount, 12)
                const dispSp = bh / (dispRows + 1)
                const annotY1 = by + dispSp
                const annotY2 = by + dispSp * 2
                return (
                  <g>
                    {/* Bracket between two rows */}
                    <line x1={bx - 2} y1={annotY1} x2={bx - 8} y2={annotY1} stroke="#7c3aed" strokeWidth={0.8} />
                    <line x1={bx - 8} y1={annotY1} x2={bx - 8} y2={annotY2} stroke="#7c3aed" strokeWidth={0.8} />
                    <line x1={bx - 2} y1={annotY2} x2={bx - 8} y2={annotY2} stroke="#7c3aed" strokeWidth={0.8} />
                    <text x={bx - 11} y={(annotY1 + annotY2) / 2} textAnchor="end"
                      fontSize={7} fontWeight="500" fill="#7c3aed" dominantBaseline="middle">
                      {block.row_spacing_cm} cm
                    </text>
                    <text x={bx - 11} y={(annotY1 + annotY2) / 2 + 9} textAnchor="end"
                      fontSize={6} fill="#7c3aed" dominantBaseline="middle">
                      (row gap)
                    </text>
                  </g>
                )
              })() : null}

              {/* ── Plant spacing annotation (between dots on first row) ── */}
              {block.plant_spacing_cm > 0 && bw > 90 && rowCount > 1 ? (() => {
                const dispRows = Math.min(rowCount, 12)
                const dispSp = bh / (dispRows + 1)
                const dotsPerRow = Math.min(6, Math.floor((bw - 16) / 10))
                if (dotsPerRow < 2) return null
                const dotSpacing = (bw - 16) / (dotsPerRow + 1)
                const dotY = by + dispSp - 8
                const d1x = bx + 8 + dotSpacing
                const d2x = bx + 8 + dotSpacing * 2
                return (
                  <g>
                    <line x1={d1x} y1={dotY} x2={d2x} y2={dotY} stroke="#0891b2" strokeWidth={0.8} />
                    <line x1={d1x} y1={dotY - 3} x2={d1x} y2={dotY + 3} stroke="#0891b2" strokeWidth={0.8} />
                    <line x1={d2x} y1={dotY - 3} x2={d2x} y2={dotY + 3} stroke="#0891b2" strokeWidth={0.8} />
                    <text x={(d1x + d2x) / 2} y={dotY - 4} textAnchor="middle"
                      fontSize={6.5} fontWeight="500" fill="#0891b2">
                      {block.plant_spacing_cm} cm (plant gap)
                    </text>
                  </g>
                )
              })() : null}

              {/* ── Width dimension below block ── */}
              {block.field_width_m ? (
                <DimensionLine
                  x1={bx} y1={by + bh} x2={bx + bw} y2={by + bh}
                  label={`← ${block.field_width_m} m width →`}
                  color="#334155" offset={14} side="bottom"
                />
              ) : null}

              {/* ── Length dimension on right side (first block only to avoid clutter) ── */}
              {i === 0 && block.field_length_m ? (
                <DimensionLine
                  x1={bx + bw} y1={by} x2={bx + bw} y2={by + bh}
                  label={`${block.field_length_m} m length`}
                  color="#334155" offset={14} side="right"
                />
              ) : null}

              {/* Rows × plants summary at bottom of block */}
              {block.rows > 0 && bw > 55 ? (
                <text x={bx + bw / 2} y={by + bh - 8} textAnchor="middle"
                  fontSize={7.5} fill="#475569">
                  {block.rows} rows × {block.plants_per_row} plants/row
                </text>
              ) : null}

              {/* ── Pathway dimension between blocks ── */}
              {i < blocks.length - 1 ? (
                <g>
                  {/* Pathway fill */}
                  <rect
                    x={bx + bw + 1} y={by + bh / 2 - 20}
                    width={pathwayGap - 2} height={40}
                    fill="#f1f5f9" rx={2}
                  />
                  <text
                    x={bx + bw + pathwayGap / 2} y={by + bh / 2 - 4}
                    textAnchor="middle" fontSize={6.5} fontWeight="500" fill="#64748b">
                    {pathwayWidth} m
                  </text>
                  <text
                    x={bx + bw + pathwayGap / 2} y={by + bh / 2 + 6}
                    textAnchor="middle" fontSize={5.5} fill="#94a3b8">
                    path
                  </text>
                </g>
              ) : null}
            </g>
          )
        })}

        {/* ── Legend ── */}
        <g transform={`translate(${padding}, ${mapHeight - bottomMargin + 15})`}>
          <text x={0} y={0} fontSize={8} fontWeight="600" fill="#475569">Legend:</text>
          {/* Row spacing */}
          <line x1={50} y1={-3} x2={70} y2={-3} stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="3,3" />
          <text x={74} y={0} fontSize={7} fill="#7c3aed">Row spacing (between rows)</text>
          {/* Plant spacing */}
          <circle cx={200} cy={-3} r={2.5} fill="#0891b2" />
          <circle cx={210} cy={-3} r={2.5} fill="#0891b2" />
          <line x1={200} y1={-8} x2={210} y2={-8} stroke="#0891b2" strokeWidth={0.8} />
          <text x={216} y={0} fontSize={7} fill="#0891b2">Plant spacing (between plants)</text>
          {/* Dimension */}
          <line x1={340} y1={-3} x2={365} y2={-3} stroke="#334155" strokeWidth={0.8} />
          <line x1={340} y1={-6} x2={340} y2={0} stroke="#334155" strokeWidth={0.8} />
          <line x1={365} y1={-6} x2={365} y2={0} stroke="#334155" strokeWidth={0.8} />
          <text x={370} y={0} fontSize={7} fill="#334155">Field dimensions (metres)</text>
          {/* Border strip */}
          <line x1={490} y1={-3} x2={515} y2={-3} stroke="#16a34a" strokeWidth={1.5} strokeDasharray="4,3" />
          <text x={520} y={0} fontSize={7} fill="#16a34a">Border / windbreak strip</text>
        </g>

        {/* Border label */}
        <text x={mapWidth / 2} y={mapHeight - 6} textAnchor="middle" fontSize={8} fill="#16a34a">
          ── plant border / windbreak crops around entire field perimeter ──
        </text>
      </svg>
    </div>
  )
}

/* ── Layout Structure Overview Graph ───────────────────────────────── */

function LayoutOverviewGraph({ blocks }: { blocks: FieldBlock[] }) {
  if (blocks.length === 0) return null

  const totalArea = blocks.reduce((s, b) => s + b.area_acres, 0)
  const totalPlants = blocks.reduce((s, b) => s + b.total_plants, 0)
  const maxPlants = Math.max(...blocks.map(b => b.total_plants))
  const maxRowSpacing = Math.max(...blocks.map(b => b.row_spacing_cm))
  const maxPlantSpacing = Math.max(...blocks.map(b => b.plant_spacing_cm))
  const maxSpacing = Math.max(maxRowSpacing, maxPlantSpacing, 1)

  const w = 760
  const leftLabel = 110 // space for crop names on left
  const rightPad = 30
  const chartW = w - leftLabel - rightPad

  // Section heights
  const headerH = 60
  const areaBarH = 50
  const gapAfterArea = 30
  const barH = 28 // height of each bar row
  const barGap = 6
  const blockRowH = barH * 2 + barGap + 22 // two bars + gap + block label
  const densitySectionTop = headerH + areaBarH + gapAfterArea
  const spacingSectionTop = densitySectionTop + blocks.length * blockRowH + 50

  // Dynamic height
  const totalH = spacingSectionTop + blocks.length * blockRowH + 45

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
      <h3 className="mb-1 text-base font-semibold text-slate-800">
        Layout Plan Structure
      </h3>
      <p className="mb-4 text-xs text-slate-500">
        Visual comparison of area allocation, plant counts, and spacing across all blocks.
        Helps you understand the overall plan balance at a glance.
      </p>

      <svg viewBox={`0 0 ${w} ${totalH}`} className="w-full rounded-lg border border-slate-200 bg-slate-50">

        {/* ═══════ SECTION 1: Area Distribution Bar ═══════ */}
        <text x={w / 2} y={22} textAnchor="middle" fontSize={11} fontWeight="600" fill="#334155">
          Area Distribution — {totalArea.toFixed(2)} acres total
        </text>

        {/* Stacked horizontal bar */}
        {(() => {
          const barY = 34
          const barHeight = 22
          let xOffset = leftLabel
          return (
            <g>
              {/* Background */}
              <rect x={leftLabel} y={barY} width={chartW} height={barHeight} rx={4}
                fill="#f1f5f9" stroke="#cbd5e1" strokeWidth={0.5} />
              {blocks.map((block, i) => {
                const color = BLOCK_COLORS[i % BLOCK_COLORS.length]
                const fraction = block.area_acres / totalArea
                const segW = fraction * chartW
                const segX = xOffset
                xOffset += segW
                return (
                  <g key={`area-${i}`}>
                    <rect x={segX} y={barY} width={segW} height={barHeight}
                      rx={i === 0 ? 4 : 0}
                      fill={color.fill} fillOpacity={0.6}
                      stroke={color.stroke} strokeWidth={1}
                    />
                    {/* Label inside segment if wide enough */}
                    {segW > 55 ? (
                      <>
                        <text x={segX + segW / 2} y={barY + 10} textAnchor="middle"
                          fontSize={8} fontWeight="600" fill={color.stroke}>
                          {block.crop_name}
                        </text>
                        <text x={segX + segW / 2} y={barY + 19} textAnchor="middle"
                          fontSize={7} fill="#475569">
                          {block.area_acres} ac ({(fraction * 100).toFixed(0)}%)
                        </text>
                      </>
                    ) : (
                      <text x={segX + segW / 2} y={barY + 14} textAnchor="middle"
                        fontSize={7} fontWeight="600" fill={color.stroke}>
                        {(fraction * 100).toFixed(0)}%
                      </text>
                    )}
                  </g>
                )
              })}
              {/* Label */}
              <text x={leftLabel - 6} y={barY + 14} textAnchor="end"
                fontSize={8} fontWeight="500" fill="#64748b">
                Area (acres)
              </text>
            </g>
          )
        })()}

        {/* ═══════ SECTION 2: Plant Count Comparison ═══════ */}
        <text x={w / 2} y={densitySectionTop - 10} textAnchor="middle"
          fontSize={11} fontWeight="600" fill="#334155">
          Plant Count per Block — {fmt(totalPlants)} total plants
        </text>
        {/* Axis line */}
        <line x1={leftLabel} y1={densitySectionTop + 2} x2={leftLabel}
          y2={densitySectionTop + blocks.length * blockRowH - 16}
          stroke="#cbd5e1" strokeWidth={0.5} />
        <line x1={leftLabel} y1={densitySectionTop + blocks.length * blockRowH - 16}
          x2={leftLabel + chartW}
          y2={densitySectionTop + blocks.length * blockRowH - 16}
          stroke="#cbd5e1" strokeWidth={0.5} />

        {blocks.map((block, i) => {
          const color = BLOCK_COLORS[i % BLOCK_COLORS.length]
          const bY = densitySectionTop + i * blockRowH + 8
          const barWidth = maxPlants > 0 ? (block.total_plants / maxPlants) * (chartW - 40) : 0

          return (
            <g key={`density-${i}`}>
              {/* Block label */}
              <text x={leftLabel - 6} y={bY + barH / 2 + 3} textAnchor="end"
                fontSize={9} fontWeight="600" fill={color.stroke}>
                {block.block_label}
              </text>
              <text x={leftLabel - 6} y={bY + barH / 2 + 14} textAnchor="end"
                fontSize={7} fill="#64748b">
                {block.crop_name}
              </text>

              {/* Bar */}
              <rect x={leftLabel + 4} y={bY} width={barWidth} height={barH}
                rx={4} fill={color.fill} fillOpacity={0.5}
                stroke={color.stroke} strokeWidth={1.2} />

              {/* Plant count label */}
              <text x={leftLabel + barWidth + 10} y={bY + barH / 2 + 4}
                fontSize={9} fontWeight="600" fill="#334155">
                {fmt(block.total_plants)} plants
              </text>

              {/* Sub-detail: rows x plants/row */}
              <text x={leftLabel + 8} y={bY + barH + 14}
                fontSize={7} fill="#94a3b8">
                {block.rows} rows x {block.plants_per_row} plants/row = {fmt(block.total_plants)}
                {' '} | {block.area_acres} acres
                {' '} | Density: {fmt(Math.round(block.total_plants / Math.max(block.area_acres, 0.01)))}/acre
              </text>
            </g>
          )
        })}

        {/* Axis label */}
        <text x={leftLabel + chartW / 2}
          y={densitySectionTop + blocks.length * blockRowH - 4}
          textAnchor="middle" fontSize={7} fill="#94a3b8">
          Plant Count →
        </text>

        {/* ═══════ SECTION 3: Spacing Comparison (grouped bars) ═══════ */}
        <text x={w / 2} y={spacingSectionTop - 10} textAnchor="middle"
          fontSize={11} fontWeight="600" fill="#334155">
          Spacing Comparison — Row vs Plant Spacing (cm)
        </text>

        {/* Axis */}
        <line x1={leftLabel} y1={spacingSectionTop + 2} x2={leftLabel}
          y2={spacingSectionTop + blocks.length * blockRowH - 16}
          stroke="#cbd5e1" strokeWidth={0.5} />
        <line x1={leftLabel}
          y1={spacingSectionTop + blocks.length * blockRowH - 16}
          x2={leftLabel + chartW}
          y2={spacingSectionTop + blocks.length * blockRowH - 16}
          stroke="#cbd5e1" strokeWidth={0.5} />

        {/* Grid lines + scale */}
        {[0.25, 0.5, 0.75, 1.0].map(frac => {
          const gx = leftLabel + frac * (chartW - 40)
          const val = Math.round(frac * maxSpacing)
          return (
            <g key={`grid-${frac}`}>
              <line x1={gx} y1={spacingSectionTop + 2}
                x2={gx}
                y2={spacingSectionTop + blocks.length * blockRowH - 16}
                stroke="#e2e8f0" strokeWidth={0.5} strokeDasharray="3,3" />
              <text x={gx}
                y={spacingSectionTop + blocks.length * blockRowH - 6}
                textAnchor="middle" fontSize={7} fill="#94a3b8">
                {val} cm
              </text>
            </g>
          )
        })}

        {blocks.map((block, i) => {
          const color = BLOCK_COLORS[i % BLOCK_COLORS.length]
          const groupY = spacingSectionTop + i * blockRowH + 8
          const rowBarW = maxSpacing > 0 ? (block.row_spacing_cm / maxSpacing) * (chartW - 40) : 0
          const plantBarW = maxSpacing > 0 ? (block.plant_spacing_cm / maxSpacing) * (chartW - 40) : 0

          return (
            <g key={`spacing-${i}`}>
              {/* Block label */}
              <text x={leftLabel - 6} y={groupY + barH / 2 + 3} textAnchor="end"
                fontSize={9} fontWeight="600" fill={color.stroke}>
                {block.block_label}
              </text>
              <text x={leftLabel - 6} y={groupY + barH / 2 + 14} textAnchor="end"
                fontSize={7} fill="#64748b">
                {block.crop_name}
              </text>

              {/* Row spacing bar (purple) */}
              <rect x={leftLabel + 4} y={groupY} width={rowBarW} height={barH / 2 + 2}
                rx={3} fill="#c4b5fd" fillOpacity={0.7}
                stroke="#7c3aed" strokeWidth={1} />
              <text x={leftLabel + rowBarW + 10} y={groupY + barH / 4 + 4}
                fontSize={8} fontWeight="500" fill="#7c3aed">
                {block.row_spacing_cm} cm (row)
              </text>

              {/* Plant spacing bar (cyan) */}
              <rect x={leftLabel + 4} y={groupY + barH / 2 + barGap}
                width={plantBarW} height={barH / 2 + 2}
                rx={3} fill="#a5f3fc" fillOpacity={0.7}
                stroke="#0891b2" strokeWidth={1} />
              <text x={leftLabel + plantBarW + 10}
                y={groupY + barH / 2 + barGap + barH / 4 + 4}
                fontSize={8} fontWeight="500" fill="#0891b2">
                {block.plant_spacing_cm} cm (plant)
              </text>

              {/* Pattern + depth note */}
              <text x={leftLabel + 8} y={groupY + barH + barGap + 18}
                fontSize={7} fill="#94a3b8">
                Pattern: {patternLabel(block.planting_pattern)} | Depth: {block.planting_depth_cm ?? '—'} cm
                | Bed: {bedLabel(block.bed_type)}
              </text>
            </g>
          )
        })}

        {/* Legend */}
        <g transform={`translate(${leftLabel}, ${spacingSectionTop + blocks.length * blockRowH + 8})`}>
          <rect x={0} y={-5} width={chartW} height={18} rx={4}
            fill="white" stroke="#e2e8f0" strokeWidth={0.5} />
          <text x={8} y={6} fontSize={8} fontWeight="600" fill="#475569">Legend:</text>
          <rect x={55} y={-1} width={14} height={8} rx={2}
            fill="#c4b5fd" fillOpacity={0.7} stroke="#7c3aed" strokeWidth={0.8} />
          <text x={74} y={6} fontSize={7.5} fill="#7c3aed">Row spacing (distance between rows)</text>
          <rect x={280} y={-1} width={14} height={8} rx={2}
            fill="#a5f3fc" fillOpacity={0.7} stroke="#0891b2" strokeWidth={0.8} />
          <text x={299} y={6} fontSize={7.5} fill="#0891b2">Plant spacing (distance between plants in a row)</text>
        </g>
      </svg>

      {/* Summary stats row */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-emerald-50 p-3 text-center">
          <p className="text-xs font-medium text-emerald-600">Total Area</p>
          <p className="text-lg font-bold text-emerald-800">{totalArea.toFixed(2)} ac</p>
        </div>
        <div className="rounded-lg bg-blue-50 p-3 text-center">
          <p className="text-xs font-medium text-blue-600">Total Plants</p>
          <p className="text-lg font-bold text-blue-800">{fmt(totalPlants)}</p>
        </div>
        <div className="rounded-lg bg-purple-50 p-3 text-center">
          <p className="text-xs font-medium text-purple-600">Avg Density</p>
          <p className="text-lg font-bold text-purple-800">
            {fmt(Math.round(totalPlants / Math.max(totalArea, 0.01)))}/ac
          </p>
        </div>
        <div className="rounded-lg bg-amber-50 p-3 text-center">
          <p className="text-xs font-medium text-amber-600">Blocks</p>
          <p className="text-lg font-bold text-amber-800">{blocks.length}</p>
        </div>
      </div>
    </div>
  )
}

/* ── Zoomed Planting Detail (single block close-up) ───────────────── */

function ZoomedPlantingDetail({ block, index }: { block: FieldBlock; index: number }) {
  const color = BLOCK_COLORS[index % BLOCK_COLORS.length]
  const w = 400
  const h = 340
  const pad = 50
  const rows = Math.min(block.rows || 4, 5) // show up to 5 rows
  const plantsPerRow = Math.min(block.plants_per_row || 6, 6) // show up to 6 plants
  const areaW = w - pad * 2
  const areaH = h - pad * 2 - 30 // leave room for depth section
  const rowGap = areaH / (rows + 1)
  const plantGap = areaW / (plantsPerRow + 1)

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center gap-2">
        <span
          className="inline-block h-3 w-3 rounded"
          style={{ backgroundColor: color.fill, border: `2px solid ${color.stroke}` }}
        />
        <span className="text-sm font-semibold text-slate-800">
          {block.block_label}: {block.crop_name}
        </span>
        <span className="text-xs text-slate-500">— close-up planting view</span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full rounded border border-slate-100 bg-slate-50">
        {/* Field area outline */}
        <rect
          x={pad} y={pad - 10} width={areaW} height={areaH + 10}
          rx={4} fill={color.fill} fillOpacity={0.08}
          stroke={color.stroke} strokeWidth={1.5}
        />

        {/* Title */}
        <text x={w / 2} y={18} textAnchor="middle" fontSize={10} fontWeight="600" fill="#334155">
          Planting Detail — {block.crop_name}
        </text>
        <text x={w / 2} y={30} textAnchor="middle" fontSize={8} fill="#64748b">
          {patternLabel(block.planting_pattern)} pattern | {bedLabel(block.bed_type)}
        </text>

        {/* Rows + plants grid */}
        {Array.from({ length: rows }).map((_, ri) => {
          const ry = pad + (ri + 1) * rowGap - 10
          return (
            <g key={`zr-${ri}`}>
              {/* Row line */}
              <line
                x1={pad + 4} y1={ry} x2={pad + areaW - 4} y2={ry}
                stroke={color.stroke} strokeWidth={0.6} strokeOpacity={0.3} strokeDasharray="4,3"
              />
              {/* Row label */}
              <text x={pad - 4} y={ry + 3} textAnchor="end" fontSize={7} fill="#94a3b8">
                R{ri + 1}
              </text>
              {/* Plants */}
              {Array.from({ length: plantsPerRow }).map((_, pi) => {
                const px = pad + (pi + 1) * plantGap
                return (
                  <g key={`zp-${ri}-${pi}`}>
                    <circle cx={px} cy={ry} r={4} fill={color.fill} stroke={color.stroke} strokeWidth={1} />
                    {ri === 0 && pi === 0 ? (
                      <text x={px} y={ry - 8} textAnchor="middle" fontSize={6} fill="#475569">
                        Plant
                      </text>
                    ) : null}
                  </g>
                )
              })}
            </g>
          )
        })}

        {/* ── Row spacing dimension (left bracket between R1 and R2) ── */}
        {rows >= 2 ? (() => {
          const r1y = pad + rowGap - 10
          const r2y = pad + 2 * rowGap - 10
          const bx = pad - 16
          return (
            <g>
              <line x1={bx} y1={r1y} x2={bx + 6} y2={r1y} stroke="#7c3aed" strokeWidth={0.8} />
              <line x1={bx} y1={r1y} x2={bx} y2={r2y} stroke="#7c3aed" strokeWidth={0.8} />
              <line x1={bx} y1={r2y} x2={bx + 6} y2={r2y} stroke="#7c3aed" strokeWidth={0.8} />
              {/* Arrow heads */}
              <polygon points={`${bx},${r1y + 1} ${bx - 2},${r1y + 5} ${bx + 2},${r1y + 5}`} fill="#7c3aed" />
              <polygon points={`${bx},${r2y - 1} ${bx - 2},${r2y - 5} ${bx + 2},${r2y - 5}`} fill="#7c3aed" />
              <text
                x={bx - 3} y={(r1y + r2y) / 2}
                textAnchor="end" fontSize={8} fontWeight="600" fill="#7c3aed"
                dominantBaseline="middle"
              >
                {block.row_spacing_cm}
              </text>
              <text
                x={bx - 3} y={(r1y + r2y) / 2 + 10}
                textAnchor="end" fontSize={6} fill="#7c3aed"
                dominantBaseline="middle"
              >
                cm
              </text>
              <text
                x={bx - 3} y={(r1y + r2y) / 2 + 18}
                textAnchor="end" fontSize={5.5} fill="#9f7aea"
                dominantBaseline="middle"
              >
                (row gap)
              </text>
            </g>
          )
        })() : null}

        {/* ── Plant spacing dimension (top, between P1 and P2 of first row) ── */}
        {plantsPerRow >= 2 ? (() => {
          const r1y = pad + rowGap - 10
          const p1x = pad + plantGap
          const p2x = pad + 2 * plantGap
          const dimY = r1y - 18
          return (
            <g>
              <line x1={p1x} y1={dimY} x2={p2x} y2={dimY} stroke="#0891b2" strokeWidth={1} />
              <line x1={p1x} y1={dimY - 4} x2={p1x} y2={dimY + 4} stroke="#0891b2" strokeWidth={0.8} />
              <line x1={p2x} y1={dimY - 4} x2={p2x} y2={dimY + 4} stroke="#0891b2" strokeWidth={0.8} />
              {/* Arrow heads */}
              <polygon points={`${p1x + 1},${dimY} ${p1x + 5},${dimY - 2} ${p1x + 5},${dimY + 2}`} fill="#0891b2" />
              <polygon points={`${p2x - 1},${dimY} ${p2x - 5},${dimY - 2} ${p2x - 5},${dimY + 2}`} fill="#0891b2" />
              <text
                x={(p1x + p2x) / 2} y={dimY - 6}
                textAnchor="middle" fontSize={8} fontWeight="600" fill="#0891b2"
              >
                {block.plant_spacing_cm} cm
              </text>
              <text
                x={(p1x + p2x) / 2} y={dimY + 10}
                textAnchor="middle" fontSize={5.5} fill="#22d3ee"
              >
                (plant gap)
              </text>
            </g>
          )
        })() : null}

        {/* ── Planting depth cross-section (bottom of SVG) ── */}
        {block.planting_depth_cm ? (() => {
          const soilY = h - 55
          const depthPx = Math.min(30, Math.max(10, (block.planting_depth_cm ?? 3) * 3))
          const seedCx = w / 2
          return (
            <g>
              {/* Soil surface line */}
              <line x1={pad + 20} y1={soilY} x2={w - pad - 20} y2={soilY}
                stroke="#92400e" strokeWidth={1.5} />
              <text x={pad + 16} y={soilY - 3} textAnchor="end" fontSize={7} fill="#92400e">
                Soil surface
              </text>
              {/* Underground fill */}
              <rect x={pad + 20} y={soilY} width={areaW - 40} height={depthPx + 8}
                fill="#fef3c7" fillOpacity={0.5} />
              {/* Seed/plant at depth */}
              <circle cx={seedCx} cy={soilY + depthPx} r={4}
                fill="#92400e" stroke="#78350f" strokeWidth={1} />
              <text x={seedCx} y={soilY + depthPx + 3} textAnchor="middle"
                fontSize={5} fill="white" fontWeight="bold">
                S
              </text>
              {/* Depth dimension */}
              <line x1={seedCx + 20} y1={soilY} x2={seedCx + 20} y2={soilY + depthPx}
                stroke="#b45309" strokeWidth={0.8} />
              <line x1={seedCx + 16} y1={soilY} x2={seedCx + 24} y2={soilY}
                stroke="#b45309" strokeWidth={0.8} />
              <line x1={seedCx + 16} y1={soilY + depthPx} x2={seedCx + 24} y2={soilY + depthPx}
                stroke="#b45309" strokeWidth={0.8} />
              <text x={seedCx + 28} y={soilY + depthPx / 2 + 3} fontSize={8}
                fontWeight="600" fill="#b45309">
                {block.planting_depth_cm} cm depth
              </text>
              {/* Label */}
              <text x={w / 2} y={h - 8} textAnchor="middle" fontSize={7} fill="#78350f">
                Cross-section: Sowing / Planting Depth
              </text>
            </g>
          )
        })() : null}

        {/* ── Full block stats bottom-right ── */}
        <text x={w - pad + 5} y={pad + 4} textAnchor="end" fontSize={7} fill="#64748b">
          Full block: {block.rows} rows x {block.plants_per_row} plants
        </text>
        <text x={w - pad + 5} y={pad + 14} textAnchor="end" fontSize={7} fill="#64748b">
          Total: {fmt(block.total_plants)} plants
        </text>
        {block.field_length_m && block.field_width_m ? (
          <text x={w - pad + 5} y={pad + 24} textAnchor="end" fontSize={7} fill="#64748b">
            {block.field_length_m}m x {block.field_width_m}m
          </text>
        ) : null}
      </svg>
    </div>
  )
}

/* ── Block Detail Card ─────────────────────────────────────────────── */

function BlockDetailCard({ block, index }: { block: FieldBlock; index: number }) {
  const color = BLOCK_COLORS[index % BLOCK_COLORS.length]

  return (
    <div className={`rounded-xl border-2 ${color.border} ${color.bg} ${color.text} p-5`}>
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider opacity-60">
          {block.block_label}
        </span>
        <span className="text-sm font-semibold">{block.area_acres} ac</span>
      </div>
      <p className="text-lg font-bold">{block.crop_name}</p>

      {/* Dimensions */}
      {block.field_length_m && block.field_width_m ? (
        <p className="mt-1 text-xs opacity-70">
          Field: {block.field_length_m}m × {block.field_width_m}m
        </p>
      ) : null}

      {/* Planting specs grid */}
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <div>
          <span className="opacity-60">Row spacing:</span>{' '}
          <strong>{block.row_spacing_cm} cm</strong>
        </div>
        <div>
          <span className="opacity-60">Plant spacing:</span>{' '}
          <strong>{block.plant_spacing_cm} cm</strong>
        </div>
        <div>
          <span className="opacity-60">Pattern:</span>{' '}
          <strong>{patternLabel(block.planting_pattern)}</strong>
        </div>
        <div>
          <span className="opacity-60">Depth:</span>{' '}
          <strong>{block.planting_depth_cm ?? 0} cm</strong>
        </div>
        <div>
          <span className="opacity-60">Bed type:</span>{' '}
          <strong>{bedLabel(block.bed_type)}</strong>
        </div>
        <div>
          <span className="opacity-60">Total plants:</span>{' '}
          <strong>{fmt(block.total_plants)}</strong>
        </div>
        {block.rows > 0 && (
          <>
            <div>
              <span className="opacity-60">Rows:</span>{' '}
              <strong>{block.rows}</strong>
            </div>
            <div>
              <span className="opacity-60">Plants/row:</span>{' '}
              <strong>{block.plants_per_row}</strong>
            </div>
          </>
        )}
      </div>

      {/* Seed rate / spacing note */}
      {block.seed_rate_hint ? (
        <p className="mt-2 rounded-md bg-white/50 px-2 py-1 text-xs italic opacity-80">
          {block.seed_rate_hint}
        </p>
      ) : null}

      {/* Irrigation */}
      {block.irrigation_method ? (
        <div className="mt-3 flex items-start gap-1.5 text-xs">
          <span className="mt-0.5 shrink-0">💧</span>
          <span>{block.irrigation_method}</span>
        </div>
      ) : null}

      {/* Planting tip */}
      {block.planting_tip ? (
        <div className="mt-2 flex items-start gap-1.5 text-xs">
          <span className="mt-0.5 shrink-0">🌱</span>
          <span>{block.planting_tip}</span>
        </div>
      ) : null}

      {/* Companion crops */}
      {block.companion_crops && block.companion_crops.length > 0 ? (
        <div className="mt-2">
          <p className="text-xs font-semibold opacity-60">Companion crops:</p>
          <ul className="mt-0.5 list-inside list-disc text-xs opacity-80">
            {block.companion_crops.map((c, ci) => (
              <li key={ci}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

/* ── Main Component ────────────────────────────────────────────────── */

export function FieldLayoutResults({ layout }: { layout: FieldLayoutPlan }) {
  const { blocks, notes, field_orientation, pathway_width_m, border_crop, irrigation_layout, expert_tips } = layout

  return (
    <div className="space-y-6">
      {/* Visual field map */}
      <FieldMapVisualization blocks={blocks} pathwayWidth={pathway_width_m ?? 1.5} />

      {/* Layout structure overview graph */}
      <LayoutOverviewGraph blocks={blocks} />

      {/* Zoomed planting diagrams */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-1 text-base font-semibold text-slate-800">
          Close-up Planting Diagrams
        </h3>
        <p className="mb-4 text-xs text-slate-500">
          Zoomed-in view of each block showing exact row spacing, plant spacing, planting depth, and pattern.
          Use these diagrams as a field reference when planting.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {blocks.map((block, i) => (
            <ZoomedPlantingDetail key={block.block_label} block={block} index={i} />
          ))}
        </div>
      </div>

      {/* Block detail cards */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-1 text-base font-semibold text-slate-800">Block-wise Planting Guide</h3>
        <p className="mb-4 text-xs text-slate-500">
          Detailed planting instructions for each block — spacing, pattern, depth, and irrigation.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {blocks.map((block, i) => (
            <BlockDetailCard key={block.block_label} block={block} index={i} />
          ))}
        </div>
      </div>

      {/* Spacing reference table */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-800">Quick Reference Table</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-200 text-left text-slate-600">
                <th className="pb-2 pr-3">Block</th>
                <th className="pb-2 pr-3">Crop</th>
                <th className="pb-2 pr-3 text-right">Area</th>
                <th className="pb-2 pr-3 text-right">Row (cm)</th>
                <th className="pb-2 pr-3 text-right">Plant (cm)</th>
                <th className="pb-2 pr-3 text-right">Plants</th>
                <th className="pb-2 pr-3">Pattern</th>
                <th className="pb-2 text-right">Depth (cm)</th>
              </tr>
            </thead>
            <tbody>
              {blocks.map((b) => (
                <tr key={b.block_label} className="border-b border-surface-100">
                  <td className="py-2 pr-3 font-medium">{b.block_label}</td>
                  <td className="py-2 pr-3">{b.crop_name}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.area_acres} ac</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.row_spacing_cm}</td>
                  <td className="py-2 pr-3 text-right font-mono">{b.plant_spacing_cm}</td>
                  <td className="py-2 pr-3 text-right font-mono">{fmt(b.total_plants)}</td>
                  <td className="py-2 pr-3 text-xs">{patternLabel(b.planting_pattern)}</td>
                  <td className="py-2 text-right font-mono">{b.planting_depth_cm ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Field Planning Advice */}
      <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-slate-800">Field Planning Advice</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Orientation */}
          {field_orientation ? (
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="mb-1 text-xs font-semibold text-blue-700">Row Orientation</p>
              <p className="text-sm text-blue-900">{field_orientation}</p>
            </div>
          ) : null}

          {/* Irrigation layout */}
          {irrigation_layout ? (
            <div className="rounded-lg bg-cyan-50 p-4">
              <p className="mb-1 text-xs font-semibold text-cyan-700">Irrigation Layout</p>
              <p className="text-sm text-cyan-900">{irrigation_layout}</p>
            </div>
          ) : null}

          {/* Border crop */}
          {border_crop ? (
            <div className="rounded-lg bg-green-50 p-4">
              <p className="mb-1 text-xs font-semibold text-green-700">Border / Windbreak Crop</p>
              <p className="text-sm text-green-900">{border_crop}</p>
            </div>
          ) : null}

          {/* Pathway */}
          {pathway_width_m ? (
            <div className="rounded-lg bg-slate-100 p-4">
              <p className="mb-1 text-xs font-semibold text-slate-600">Pathways</p>
              <p className="text-sm text-slate-800">
                Maintain {pathway_width_m} m wide pathways between blocks for equipment access,
                spraying, and harvest transportation.
              </p>
            </div>
          ) : null}
        </div>
      </div>

      {/* Expert Tips */}
      {expert_tips && expert_tips.length > 0 ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <h3 className="mb-3 text-base font-semibold text-emerald-900">
            Expert Tips
          </h3>
          <ul className="space-y-2">
            {expert_tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-emerald-800">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-200 text-xs font-bold text-emerald-700">
                  {i + 1}
                </span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Layout Notes */}
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
