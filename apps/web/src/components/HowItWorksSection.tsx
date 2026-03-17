import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const stepIcons = [
  'M15 10.5a3 3 0 11-6 0 3 3 0 016 0z M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z', // map pin
  'M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25z', // cpu
  'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z', // document
]

const agentPipeline = [
  { label: 'Validate', agents: ['Input Validator'] },
  { label: 'Filter', agents: ['Constraint Filter', 'Soil Filter'] },
  {
    label: 'Score',
    agents: ['Soil Scorer', 'Water Scorer', 'Climate Scorer', 'Market Scorer', 'Risk Scorer', 'Financial Scorer'],
  },
  { label: 'Plan', agents: ['Crop Planner'] },
  { label: 'Verify', agents: ['Agronomist Reviewer'] },
]

const steps = [
  {
    num: '01',
    title: 'Tell Us About Your Farm',
    body: 'Share your location, land area, water availability, irrigation source, budget, labour, farming goal, time horizon, and risk tolerance. These 9 inputs are all GrowGrid needs.',
    visual: (
      <div className="space-y-2">
        {[
          ['State', 'Maharashtra'],
          ['Land', '2 acres'],
          ['Goal', 'Stable Income'],
          ['Soil', 'Loamy'],
          ['Water', 'Borewell'],
        ].map(([label, value], i) => (
          <motion.div
            key={label}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.4, delay: 0.6 + i * 0.1 }}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-2.5"
          >
            <span className="text-xs font-medium text-gray-500">{label}</span>
            <span className="text-sm font-semibold text-forest">{value}</span>
          </motion.div>
        ))}
      </div>
    ),
  },
  {
    num: '02',
    title: '11 Specialist Agents Build Your Plan',
    body: "GrowGrid runs your inputs through 11 agents in sequence. First, hard filters remove crops and practices that don't fit your constraints. Then, weighted scoring across 6 dimensions ranks what remains. Finally, an agronomist agent cross-checks every recommendation.",
    visual: (
      <div className="space-y-3 py-1">
        {/* Phase pipeline — arrows are siblings of phase nodes, not children */}
        <div className="flex items-center">
          {agentPipeline.flatMap((phase, i) => {
            const nodes = [
              <motion.div
                key={phase.label}
                initial={{ opacity: 0, scale: 0.85 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.35, delay: 0.5 + i * 0.15 }}
                className="flex flex-shrink-0 flex-col items-center gap-1.5"
              >
                <div className="relative flex h-10 w-10 items-center justify-center rounded-full border border-primary-400/50 bg-primary-400/15 text-xs font-bold text-primary-600">
                  {phase.agents.length}
                  {phase.agents.length > 1 && (
                    <span className="absolute -right-1 -top-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-primary-500 text-[7px] font-bold leading-none text-white">
                      ×
                    </span>
                  )}
                </div>
                <span className="text-[9px] font-semibold uppercase tracking-wide text-gray-500">
                  {phase.label}
                </span>
              </motion.div>,
            ]
            if (i < agentPipeline.length - 1) {
              nodes.push(
                <motion.div
                  key={`arrow-${i}`}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: 0.65 + i * 0.15 }}
                  className="mb-[18px] flex flex-1 items-center px-1"
                >
                  <svg width="100%" height="10" viewBox="0 0 32 10" preserveAspectRatio="none" fill="none">
                    <line x1="0" y1="5" x2="24" y2="5" stroke="#86efac" strokeWidth="1.5" strokeDasharray="4 2" />
                    <path d="M21 2l3.5 3-3.5 3" stroke="#86efac" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.div>
              )
            }
            return nodes
          })}
        </div>

        {/* All 11 agent chips */}
        <div className="flex flex-wrap gap-1.5 border-t border-gray-100 pt-3">
          {agentPipeline.flatMap((phase, pi) =>
            phase.agents.map((agent, ai) => (
              <motion.span
                key={agent}
                initial={{ opacity: 0, y: 4 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.25, delay: 1.0 + (pi * 3 + ai) * 0.05 }}
                className="rounded-full border border-primary-200 bg-primary-50 px-2.5 py-0.5 text-[10px] font-medium text-primary-700"
              >
                {agent}
              </motion.span>
            ))
          )}
        </div>

        <p className="text-right text-[10px] font-medium text-gray-400">
          11 agents · sequential execution
        </p>
      </div>
    ),
  },
  {
    num: '03',
    title: 'Receive Your 17-Section Farm Report',
    body: 'Your report covers: recommended farming practice, crop portfolio with area allocation, grow guides, 3-scenario financials, government scheme matches (like PM-KISAN, PMFBY, and KCC — Kisan Credit Card), risk matrix, field layout, and a month-by-month execution roadmap.',
    visual: (
      <div className="space-y-2">
        {[
          'Farm Profile & SWOT',
          'Crop Portfolio & Grow Guides',
          'Financial Projections',
          'Risk Matrix',
          'Govt Scheme Matches',
          'Month-by-Month Roadmap',
        ].map((s, i) => (
          <motion.div
            key={s}
            initial={{ opacity: 0, x: 10 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: 0.6 + i * 0.1 }}
            className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2"
          >
            <span className="text-primary-500">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6L9 17l-5-5" /></svg>
            </span>
            <span className="text-sm font-medium text-forest">{s}</span>
          </motion.div>
        ))}
      </div>
    ),
  },
]

export function HowItWorksSection() {
  const { ref, inView } = useInView({ threshold: 0.1, triggerOnce: true })

  return (
    <section id="how-it-works" className="bg-cream py-24 sm:py-32">
      <div ref={ref} className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 text-sm font-semibold tracking-wider text-primary-500 uppercase"
        >
          How It Works
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-16 font-display text-4xl font-normal leading-tight text-forest sm:text-5xl"
        >
          Answer 9 questions. Get a complete farm plan.
          <br />
          <span className="font-display italic text-primary-500">In minutes.</span>
        </motion.h2>

        {/* Steps */}
        <div className="space-y-16 md:space-y-24">
          {steps.map((step, i) => (
            <motion.div
              key={step.num}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className={`flex flex-col gap-8 md:flex-row md:items-start md:gap-16 ${
                i % 2 === 1 ? 'md:flex-row-reverse' : ''
              }`}
            >
              {/* Text */}
              <div className="flex-1">
                <div className="mb-4 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-forest">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d={stepIcons[i]} />
                    </svg>
                  </span>
                  <span className="text-xs font-bold tracking-wider text-primary-500 uppercase">
                    Step {step.num}
                  </span>
                </div>
                <h3 className="mb-3 text-2xl font-bold text-forest">{step.title}</h3>
                <p className="text-base leading-relaxed text-gray-600">{step.body}</p>
              </div>

              {/* Visual */}
              <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-6 shadow-md">
                {step.visual}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
