import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const agents = [
  { num: 1, abbr: 'CL', name: 'Clarification', detail: 'Asks follow-up questions to resolve ambiguity before analysis begins.' },
  { num: 2, abbr: 'VA', name: 'Validation', detail: 'Checks feasibility of land area, budget, water, and labour combinations.' },
  { num: 3, abbr: 'GC', name: 'Goal Classifier', detail: 'Maps "maximize profit" into weighted dimensions like ROI, risk, and water efficiency.' },
  { num: 4, abbr: 'PR', name: 'Practice Recommender', detail: 'Chooses between open field, drip horticulture, polyhouse, orchard, etc.' },
  { num: 5, abbr: 'CR', name: 'Crop Recommender', detail: 'Scores crops across 6 dimensions and selects the best-fit portfolio.' },
  { num: 6, abbr: 'AV', name: 'Agronomist Verifier', detail: 'Cross-references every crop recommendation with live agronomic data.' },
  { num: 7, abbr: 'MI', name: 'Market Intelligence', detail: 'Finds nearby mandis, historical price data, and farmer producer organizations.' },
  { num: 8, abbr: 'EC', name: 'Economist Agent', detail: 'Generates 3-scenario financials: conservative, base, and optimistic.' },
  { num: 9, abbr: 'WP', name: 'Water Planner', detail: 'Calculates water needs by crop, month, and irrigation method.' },
  { num: 10, abbr: 'GS', name: 'Govt Schemes', detail: 'Finds PM-KISAN, PMFBY, state subsidies, and KCC eligibility.' },
  { num: 11, abbr: 'RC', name: 'Report Composer', detail: 'Compiles the final report with all agent outputs, formatted for action.' },
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
          The Engine
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 text-center font-display text-4xl font-normal leading-tight text-white sm:text-5xl"
        >
          11 specialist agents.
          <br />
          <span className="font-display italic text-primary-300">One complete farm plan.</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mb-16 max-w-3xl text-center text-lg text-[#8A8F98] md:text-xl"
        >
          Each agent handles exactly one job — and passes its enriched output to the next.
          No black boxes. No hallucinated recommendations. Every decision is traceable.
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
