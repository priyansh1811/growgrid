import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const agents = [
  { num: 1, abbr: 'CL', name: 'Clarification', detail: 'Checks if any of your 9 inputs need clarification before analysis starts.' },
  { num: 2, abbr: 'VA', name: 'Validation', detail: 'Confirms your land, budget, water, and labour combination is realistic and viable.' },
  { num: 3, abbr: 'GC', name: 'Goal Classifier', detail: 'Translates your farming goal (e.g. "maximize profit" or "stable income") into scoring weights for crop selection.' },
  { num: 4, abbr: 'PR', name: 'Practice Recommender', detail: 'Picks the best farming practice from 18 options (open field, drip horticulture, polyhouse, orchard, etc.) based on your constraints.' },
  { num: 5, abbr: 'CR', name: 'Crop Recommender', detail: 'Scores crops from a database of 86 across 6 dimensions (water, soil, season, goal, labour, risk) and picks the best-fit portfolio.' },
  { num: 6, abbr: 'AV', name: 'Agronomist Verifier', detail: 'Uses AI + web search to cross-check each recommended crop against real agronomic sources.' },
  { num: 7, abbr: 'MI', name: 'Market Intelligence', detail: 'Identifies nearby mandis (wholesale markets), recent price trends, and farmer producer organisations for your crops.' },
  { num: 8, abbr: 'EC', name: 'Economist Agent', detail: 'Builds 3-scenario financial projections — conservative, base, and optimistic — with revenue, costs, and net profit.' },
  { num: 9, abbr: 'WP', name: 'Water Planner', detail: 'Estimates water demand by crop, month, and irrigation type — and flags shortfalls early.' },
  { num: 10, abbr: 'GS', name: 'Govt Schemes', detail: 'Matches you to relevant government schemes — PM-KISAN (income support), PMFBY (crop insurance), KCC (Kisan Credit Card loans), and state subsidies.' },
  { num: 11, abbr: 'RC', name: 'Report Composer', detail: 'Assembles the full 17-section advisory report from all agent outputs, ready to read and act on.' },
]

export function AgentPipelineSection() {
  const [hoveredAgent, setHoveredAgent] = useState<number | null>(null)
  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="agents" className="py-24 sm:py-32" style={{ backgroundColor: '#0C0D10' }}>
      <div ref={ref} className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 text-center text-sm font-semibold tracking-wider text-primary-300 uppercase"
        >
          Under the hood
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 text-center font-display text-4xl font-normal leading-tight text-white sm:text-5xl"
        >
          11 agents, each with one job.
          <br />
          <span className="font-display italic text-primary-300">Together, one complete plan.</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mb-16 max-w-3xl text-center text-lg text-[#8A8F98] md:text-xl"
        >
          Your inputs flow through 11 agents in sequence. Each agent handles one specific task —
          validation, crop scoring, financial modelling, risk analysis — and passes its output to the
          next. Every step is traceable.
        </motion.p>

        {/* Pipeline — horizontal scroll on mobile */}
        <div className="overflow-x-auto pb-4">
          <div className="relative mx-auto flex min-w-[900px] items-start justify-between gap-0 px-4">
            {/* Connector line */}
            <svg
              className="pointer-events-none absolute left-[40px] top-[24px] z-0"
              width="calc(100% - 80px)"
              height="4"
              style={{ width: 'calc(100% - 80px)' }}
            >
              <line
                x1="0"
                y1="2"
                x2="100%"
                y2="2"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth="2"
                strokeDasharray="6 4"
                className="animate-dash-flow"
              />
            </svg>

            {agents.map((agent, i) => (
              <div key={agent.num} className="relative z-10 flex flex-col items-center" style={{ flex: '1 0 0' }}>
                <motion.div
                  initial={{ opacity: 0.3, scale: 0.8 }}
                  animate={
                    inView
                      ? { opacity: 1, scale: 1 }
                      : {}
                  }
                  transition={{ duration: 0.4, delay: 0.3 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
                  onMouseEnter={() => setHoveredAgent(agent.num)}
                  onMouseLeave={() => setHoveredAgent(null)}
                  className="relative cursor-pointer"
                >
                  {/* Node */}
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-full border border-white/10 text-[11px] font-bold text-primary-300 transition-all duration-300 hover:border-primary-400/50 hover:bg-white/5"
                    style={{ backgroundColor: '#17181C' }}
                  >
                    {agent.abbr}
                  </div>

                  {/* Tooltip */}
                  <AnimatePresence>
                    {hoveredAgent === agent.num && (
                      <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute bottom-full left-1/2 z-20 mb-3 w-56 -translate-x-1/2 rounded-xl border border-white/10 p-4 text-left shadow-xl backdrop-blur-lg"
                        style={{ backgroundColor: '#1E1F24' }}
                      >
                        <p className="mb-1 text-xs font-bold text-white">
                          {agent.num.toString().padStart(2, '0')}. {agent.name}
                        </p>
                        <p className="text-xs leading-relaxed text-white/50">
                          {agent.detail}
                        </p>
                        <div
                          className="absolute -bottom-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r border-white/10"
                          style={{ backgroundColor: '#1E1F24' }}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* Label */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={inView ? { opacity: 1 } : {}}
                  transition={{ duration: 0.4, delay: 0.5 + i * 0.1 }}
                  className="mt-3 text-center"
                >
                  <p className="text-[10px] font-bold text-primary-300">
                    {agent.num.toString().padStart(2, '0')}
                  </p>
                  <p className="mt-0.5 max-w-[70px] text-[10px] leading-tight text-[#8A8F98]">
                    {agent.name}
                  </p>
                </motion.div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
