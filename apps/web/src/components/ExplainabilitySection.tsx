import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const dimensions = [
  { label: 'Water Fit', pct: 82 },
  { label: 'Soil Fit', pct: 90 },
  { label: 'Goal Fit', pct: 85 },
  { label: 'Labour Fit', pct: 74 },
  { label: 'Season Fit', pct: 92 },
  { label: 'Risk Fit', pct: 80 },
]

const rejections = [
  {
    type: 'hard' as const,
    name: 'Polyhouse Cultivation',
    reason: 'Budget per acre ₹18,000 — below minimum required ₹35,000',
    tag: 'CAPEX_CONFLICT',
  },
  {
    type: 'hard' as const,
    name: 'Orchard Farming',
    reason: 'Time horizon 2 years — orchard gestation is 4–6 years',
    tag: 'GESTATION_MISMATCH',
  },
  {
    type: 'warn' as const,
    name: 'Open Field — Maize',
    reason: 'Water availability MEDIUM, Maize requires HIGH — proceed with caution',
    tag: 'WATER_STRESS',
  },
]

function CheckIcon({ className = '' }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

function XCircleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
      <circle cx="12" cy="12" r="10" />
      <path d="m15 9-6 6M9 9l6 6" />
    </svg>
  )
}

function AlertTriangleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
      <path d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  )
}

export function ExplainabilitySection() {
  const { ref: ref1, inView: inView1 } = useInView({ threshold: 0.15, triggerOnce: true })
  const { ref: ref2, inView: inView2 } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="explainability" className="bg-cream py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* ===== Block A — Scoring ===== */}
        <div
          ref={ref1}
          className="mb-24 flex flex-col gap-10 md:flex-row md:items-center md:gap-16"
        >
          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView1 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <p className="mb-3 text-sm font-semibold tracking-wider text-primary-500 uppercase">
              Explainable by Design
            </p>
            <h2 className="mb-2 font-display text-3xl font-normal text-forest sm:text-4xl">
              We don't just recommend.
            </h2>
            <p className="mb-4 font-display text-3xl italic text-primary-500 sm:text-4xl">
              We explain every decision.
            </p>
            <p className="mb-6 max-w-md text-base leading-relaxed text-gray-600">
              Every crop that makes it into your plan has a score. Every dimension —
              water fit, soil fit, goal fit, labour fit, risk fit — is calculated
              transparently. You can see exactly why a recommendation was made.
            </p>
            <ul className="space-y-2">
              {[
                '6-dimensional weighted scoring for every crop',
                'Confidence level with contributing factors shown',
                'Evidence-backed agronomic claims per crop',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 text-primary-500"><CheckIcon /></span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Score card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView1 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-lg sm:p-8">
              <p className="mb-1 text-xs font-medium text-gray-500">
                Why Tomato was recommended
              </p>
              <p className="mb-5 text-3xl font-bold text-forest">
                8.4 <span className="text-base font-normal text-gray-400">/ 10</span>
              </p>
              <div className="space-y-3">
                {dimensions.map((d, i) => (
                  <motion.div
                    key={d.label}
                    initial={{ opacity: 0 }}
                    animate={inView1 ? { opacity: 1 } : {}}
                    transition={{ duration: 0.4, delay: 0.4 + i * 0.08 }}
                  >
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-gray-700">{d.label}</span>
                      <span className="font-semibold text-forest">{d.pct}%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-gray-100">
                      <motion.div
                        className="h-2 rounded-full bg-primary-500"
                        initial={{ width: 0 }}
                        animate={inView1 ? { width: `${d.pct}%` } : {}}
                        transition={{ duration: 0.8, delay: 0.5 + i * 0.08 }}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
              <p className="mt-5 flex items-center gap-1 text-xs font-semibold text-primary-600">
                <CheckIcon className="text-primary-500" />
                Agronomist Verified
              </p>
            </div>
          </motion.div>
        </div>

        {/* ===== Block B — Rejections ===== */}
        <div
          ref={ref2}
          className="flex flex-col gap-10 md:flex-row-reverse md:items-center md:gap-16"
        >
          {/* Text */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView2 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <p className="mb-3 text-sm font-semibold tracking-wider text-primary-500 uppercase">
              Rejection Reasoning
            </p>
            <h2 className="mb-2 font-display text-3xl font-normal text-forest sm:text-4xl">
              See what was filtered out.
            </h2>
            <p className="mb-4 font-display text-3xl italic text-primary-500 sm:text-4xl">
              And exactly why.
            </p>
            <p className="mb-6 max-w-md text-base leading-relaxed text-gray-600">
              GrowGrid doesn't bury the alternatives. It tells you why polyhouse
              cultivation was eliminated, why orchard farming didn't fit, and what
              tradeoffs were made on your behalf. Full transparency.
            </p>
            <ul className="space-y-2">
              {[
                'Every rejected practice gets a reason',
                'Every filtered crop gets an explanation',
                'Cross-field conflict warnings shown explicitly',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 text-primary-500"><CheckIcon /></span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Rejection card */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView2 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-lg sm:p-8">
              <p className="mb-5 text-sm font-bold text-forest">
                Practices Not Recommended
              </p>
              <div className="space-y-4">
                {rejections.map((r, i) => (
                  <motion.div
                    key={r.name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={inView2 ? { opacity: 1, y: 0 } : {}}
                    transition={{ duration: 0.4, delay: 0.4 + i * 0.1 }}
                    className="rounded-xl border border-gray-100 bg-gray-50 p-4"
                  >
                    <div className="mb-1 flex items-center gap-2">
                      {r.type === 'hard' ? <XCircleIcon /> : <AlertTriangleIcon />}
                      <span className="text-sm font-semibold text-gray-900">{r.name}</span>
                    </div>
                    <p className="mb-2 text-xs leading-relaxed text-gray-500">
                      {r.reason}
                    </p>
                    <span className="inline-block rounded bg-red-50 px-2 py-0.5 text-[10px] font-bold text-red-600">
                      {r.tag}
                    </span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
