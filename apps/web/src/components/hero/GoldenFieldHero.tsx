import { motion } from 'framer-motion'
import { useRef } from 'react'
import { useCountUp } from '../../hooks/useCountUp'
import { useHeroParallax } from '../../hooks/useHeroParallax'

const stats = [
  { target: 86, suffix: '', prefix: '', label: 'Crops in Database' },
  { target: 25, suffix: '', prefix: '', label: 'Indian States' },
  { target: 18, suffix: '', prefix: '', label: 'Farming Practices' },
  { target: 0, suffix: '', prefix: '₹', label: 'Consulting Fee' },
]

const capabilityCards = [
  {
    title: 'Every decision explained',
    body: 'Each crop is scored across 6 dimensions — water fit, soil fit, season fit, goal fit, labour fit, and risk fit. You see the full breakdown.',
  },
  {
    title: 'Built-in financial planning',
    body: 'Your plan includes 3-scenario financial projections (conservative, base, optimistic) with revenue, costs, and net profit estimates.',
  },
  {
    title: 'Ready-to-follow roadmap',
    body: 'The report ends with a 30/60/90-day action plan — soil testing, input procurement, planting, harvest prep — all dated to your season.',
  },
]

const operatingLane = [
  { step: '01', title: 'Farm intake', body: 'You share 9 details: location, land area, water, irrigation, budget, labour, goal, time horizon, and risk tolerance.' },
  { step: '02', title: 'Analysis and scoring', body: '11 specialist agents check feasibility, match crops, model finances, and assess risks.' },
  { step: '03', title: 'Actionable report', body: 'A 17-section advisory report — crops, finances, risks, govt schemes, and an execution roadmap.' },
]

function StatMetric({
  target,
  prefix,
  suffix,
  label,
  delay,
}: {
  target: number
  prefix: string
  suffix: string
  label: string
  delay: number
}) {
  const { ref, count } = useCountUp(target, 2)

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className="surface-light rounded-[28px] p-5 sm:p-6"
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#617261]">
        Platform
      </p>
      <p className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[#16231b] sm:text-5xl">
        {prefix}
        {count}
        {suffix}
      </p>
      <p className="mt-2 text-sm font-medium uppercase tracking-[0.18em] text-[#445446]">
        {label}
      </p>
    </motion.div>
  )
}

export function GoldenFieldHero() {
  const containerRef = useRef<HTMLDivElement>(null!)

  const cloudParallax = useHeroParallax(containerRef, {
    speedX: 0.18,
    speedY: -0.2,
    smooth: true,
    stiffness: 46,
    damping: 20,
  })
  const fieldParallax = useHeroParallax(containerRef, {
    speedY: 0.28,
    smooth: true,
    stiffness: 44,
    damping: 18,
  })

  return (
    <section
      ref={containerRef}
      className="relative overflow-hidden bg-[#f5efe5] py-24 text-[#16231b] sm:py-28 lg:py-32"
    >
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-28"
        style={{
          background:
            'linear-gradient(180deg, rgba(5,10,16,1) 0%, rgba(5,10,16,0.2) 60%, rgba(245,239,229,0) 100%)',
        }}
      />

      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(circle at 14% 20%, rgba(193, 174, 135, 0.18) 0%, transparent 30%), radial-gradient(circle at 82% 12%, rgba(137, 171, 118, 0.18) 0%, transparent 26%), linear-gradient(180deg, rgba(255,255,255,0.72) 0%, rgba(245,239,229,0.92) 52%, rgba(241,232,217,1) 100%)',
          }}
        />
        <motion.img
          src="/images/hero/clouds-two.png"
          alt=""
          aria-hidden="true"
          draggable={false}
          loading="lazy"
          style={{
            x: cloudParallax.x,
            y: cloudParallax.y,
            willChange: 'transform',
          }}
          className="absolute right-[-8%] top-[-34%] w-[116%] select-none opacity-30 mix-blend-soft-light"
        />
        <motion.img
          src="/images/hero/wheat-field.png"
          alt=""
          aria-hidden="true"
          draggable={false}
          loading="lazy"
          style={{ y: fieldParallax.y, willChange: 'transform' }}
          className="absolute bottom-[-6%] right-[-8%] w-[88%] max-w-[1180px] select-none opacity-78"
        />
      </div>

      {/* Full-width decorative branch */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="pointer-events-none absolute left-1/2 top-0 z-0 h-16 w-screen -translate-x-1/2 overflow-visible sm:h-20"
      >
        <img
          src="/images/hero/long-branch.png"
          alt=""
          aria-hidden="true"
          draggable={false}
          loading="lazy"
          className="absolute left-[-745px] top-[210%] w-[80%] max-w-none -translate-y-[46%] select-none opacity-95"
        />
      </motion.div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-end lg:gap-16">
          <div className="max-w-2xl pt-10 sm:pt-14">
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="text-[11px] font-semibold uppercase tracking-[0.32em] text-[#567257]"
            >
              How it comes together
            </motion.p>

            <motion.h2
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.75, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
              className="mt-4 max-w-xl font-display text-4xl leading-tight tracking-[-0.04em] text-[#16231b] sm:text-5xl lg:text-6xl"
            >
              From your farm details to a plan you can act on.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.75, delay: 0.16, ease: [0.16, 1, 0.3, 1] }}
              className="mt-6 max-w-xl text-base leading-8 text-[#445446] sm:text-lg"
            >
              GrowGrid doesn't just suggest crops. It checks what's feasible for your land,
              scores every option, builds a financial model, and lays out a month-by-month
              execution plan.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.75, delay: 0.24, ease: [0.16, 1, 0.3, 1] }}
              className="surface-light mt-10 rounded-[30px] p-6 sm:p-7"
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#617261]">
                Three steps to your plan
              </p>

              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                {operatingLane.map((item) => (
                  <div
                    key={item.step}
                    className="rounded-2xl border border-black/6 bg-white/72 p-4"
                  >
                    <p className="text-xs font-semibold tracking-[0.24em] text-[#6b7b6a]">
                      {item.step}
                    </p>
                    <p className="mt-3 text-base font-semibold text-[#16231b]">
                      {item.title}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-[#556455]">
                      {item.body}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {capabilityCards.map((card, index) => (
              <motion.div
                key={card.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{
                  duration: 0.72,
                  delay: 0.1 + index * 0.08,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="surface-light rounded-[28px] p-6"
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="text-lg font-semibold text-[#16231b]">{card.title}</p>
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#eef4e8] text-[#4a6a47]">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.9"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-7 text-[#556455]">{card.body}</p>
              </motion.div>
            ))}

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.34, ease: [0.16, 1, 0.3, 1] }}
              className="surface-light overflow-hidden rounded-[28px] p-3"
            >
              <div className="relative h-full min-h-[240px] overflow-hidden rounded-[22px] border border-black/6 bg-[#0f1713] shadow-[0_24px_60px_rgba(7,12,9,0.16)]">
                <video
                  src="/videos/small.mp4"
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="h-full w-full object-contain object-center"
                />
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(15,23,19,0.08),rgba(15,23,19,0.48))]" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.72, delay: 0.42, ease: [0.16, 1, 0.3, 1] }}
              className="surface-light rounded-[28px] p-6 md:col-span-2"
            >
              <div className="flex flex-col gap-4 border-b border-black/6 pb-5 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#617261]">
                    What makes this different
                  </p>
                  <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-[#16231b]">
                    Database-first, not black-box AI.
                  </h3>
                </div>
                <p className="max-w-sm text-sm leading-6 text-[#556455]">
                  Most AI tools generate answers from language models alone. GrowGrid uses a
                  curated database of 86 crops, 18 practices, and 25 states as the primary
                  engine. AI is used only for verification.
                </p>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {[
                  'Hard filters eliminate options that don\'t fit your land, water, or budget — before any scoring begins.',
                  'Every crop is scored with weighted formulas across 6 dimensions. No hidden logic.',
                  'An AI verifier cross-checks recommendations with real agronomic sources as a final safety layer.',
                ].map((line) => (
                  <div
                    key={line}
                    className="rounded-2xl border border-black/6 bg-white/75 px-4 py-4 text-sm leading-6 text-[#445446]"
                  >
                    {line}
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat, index) => (
            <StatMetric key={stat.label} {...stat} delay={0.18 + index * 0.08} />
          ))}
        </div>
      </div>
    </section>
  )
}
