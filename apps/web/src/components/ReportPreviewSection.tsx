import { motion, useScroll, useTransform } from 'framer-motion'
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInView } from 'react-intersection-observer'

const chips = [
  'Farm Profile', 'SWOT Analysis', 'Crop Portfolio', 'Grow Guides',
  'Agronomic Verification', 'Market Intelligence', 'Financial Plan (3 Scenarios)',
  'Water Plan', 'Govt Schemes', 'Risk Matrix', 'Field Layout', 'Month-by-Month Roadmap',
]

export function ReportPreviewSection() {
  const navigate = useNavigate()
  const stackRef = useRef<HTMLDivElement>(null!)

  const { scrollYProgress } = useScroll({
    target: stackRef,
    offset: ['start end', 'end start'],
  })

  const card1Y = useTransform(scrollYProgress, [0, 1], [60, -30])
  const card2Y = useTransform(scrollYProgress, [0, 1], [40, -50])
  const card3Y = useTransform(scrollYProgress, [0, 1], [20, -70])

  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="report" className="bg-cream py-24 sm:py-32">
      <div ref={ref} className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-12 md:flex-row md:items-center md:gap-16">
          {/* Text — left */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <p className="mb-3 text-sm font-semibold tracking-wider text-primary-500 uppercase">
              The Advisory Report
            </p>
            <h2 className="mb-2 font-display text-3xl font-normal text-forest sm:text-4xl">
              A 17-section professional report.
            </h2>
            <p className="mb-4 font-display text-3xl italic text-primary-500 sm:text-4xl">
              Yours in minutes, for free.
            </p>
            <p className="mb-4 text-base leading-relaxed text-gray-600">
              GrowGrid produces the kind of advisory document that private agri-consultants
              charge ₹10,000–₹25,000 for. It includes your farm profile, SWOT analysis,
              crop portfolio with grow guides, 3-scenario financial projections, government
              scheme matches, a risk matrix, and a month-by-month execution roadmap.
            </p>
            <p className="mb-6 text-sm italic text-gray-500">
              Structured enough to support a KCC (Kisan Credit Card) loan application at your bank.
            </p>

            {/* Chips */}
            <div className="mb-8 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <span
                  key={chip}
                  className="rounded-full border border-primary-700 bg-forest px-3 py-1 text-xs font-medium text-primary-300"
                >
                  {chip}
                </span>
              ))}
            </div>

            <button
              onClick={() => navigate('/plan')}
              className="rounded-full bg-accent-gold px-8 py-4 text-base font-semibold text-forest transition-all duration-300 hover:bg-accent-gold-light hover:translate-y-[-1px]"
              style={{ boxShadow: '0 8px 24px rgba(200,149,108,0.25)' }}
            >
              Get My Free Farm Plan
            </button>
          </motion.div>

          {/* Visual — right: stacked report cards */}
          <div ref={stackRef} className="relative flex-1">
            <div className="relative mx-auto h-[380px] w-full max-w-[340px] sm:h-[420px]">
              {/* Card 1 — back */}
              <motion.div
                style={{ y: card1Y }}
                initial={{ opacity: 0, rotate: -2 }}
                animate={inView ? { opacity: 1, rotate: -2 } : {}}
                transition={{ duration: 0.7, delay: 0.3 }}
                className="absolute left-2 top-8 w-[90%] rounded-2xl border border-gray-200 bg-white p-5 shadow-md"
              >
                <p className="mb-3 text-xs font-bold text-forest">
                  Section 8: Financial Plan
                </p>
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="border-b border-gray-100 text-gray-400">
                      <th className="pb-1 text-left font-medium">Metric</th>
                      <th className="pb-1 text-right font-medium">Conservative</th>
                      <th className="pb-1 text-right font-medium">Base</th>
                      <th className="pb-1 text-right font-medium">Optimistic</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-600">
                    <tr><td className="py-1">Revenue</td><td className="text-right">₹1.8L</td><td className="text-right">₹2.4L</td><td className="text-right">₹3.1L</td></tr>
                    <tr><td className="py-1">Cost</td><td className="text-right">₹1.2L</td><td className="text-right">₹1.2L</td><td className="text-right">₹1.2L</td></tr>
                    <tr className="font-semibold text-forest"><td className="py-1">Net Profit</td><td className="text-right">₹0.6L</td><td className="text-right">₹1.2L</td><td className="text-right">₹1.9L</td></tr>
                  </tbody>
                </table>
              </motion.div>

              {/* Card 2 — middle */}
              <motion.div
                style={{ y: card2Y }}
                initial={{ opacity: 0, rotate: 1 }}
                animate={inView ? { opacity: 1, rotate: 1 } : {}}
                transition={{ duration: 0.7, delay: 0.45 }}
                className="absolute left-4 top-[120px] w-[90%] rounded-2xl border border-gray-200 bg-white p-5 shadow-lg"
              >
                <p className="mb-3 text-xs font-bold text-forest">
                  Section 5: Recommended Crop Portfolio
                </p>
                <div className="space-y-2">
                  {[
                    { crop: 'Tomato', acres: '1.2 acres', score: '8.4' },
                    { crop: 'Capsicum', acres: '0.8 acres', score: '7.9' },
                  ].map((c) => (
                    <div key={c.crop} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
                      <span className="text-xs font-medium text-gray-700">{c.crop} · {c.acres}</span>
                      <span className="rounded-full bg-primary-100 px-2 py-0.5 text-[10px] font-bold text-primary-700">
                        Score {c.score}
                      </span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Card 3 — front */}
              <motion.div
                style={{ y: card3Y }}
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ duration: 0.7, delay: 0.6 }}
                className="absolute left-6 top-[240px] w-[90%] rounded-2xl border border-gray-200 bg-white p-5 shadow-lg"
              >
                <p className="mb-3 text-xs font-bold text-forest">
                  Section 15: 30/60/90 Day Action Matrix
                </p>
                <div className="space-y-2 text-[10px]">
                  {[
                    { period: 'First 30 Days', action: 'Soil testing, drip system installation, nursery procurement' },
                    { period: 'Days 31–60', action: 'Transplanting, first fertigation cycle, pest monitoring setup' },
                    { period: 'Days 61–90', action: 'Growth monitoring, market linkage activation, first harvest prep' },
                  ].map((r) => (
                    <div key={r.period} className="rounded-lg bg-primary-50 px-3 py-2">
                      <p className="font-bold text-forest">{r.period}</p>
                      <p className="text-gray-500">{r.action}</p>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
