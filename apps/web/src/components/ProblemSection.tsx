import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const cards = [
  {
    title: 'Wrong Crop, Wrong Season',
    body: 'Crops chosen by local imitation — with no consideration of soil type, water availability, or seasonal timing. The result: poor yield or total loss.',
    iconPath: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z',
  },
  {
    title: 'Budget Mismatches',
    body: "Capital locked into practices the farm can't sustain. No break-even analysis. No cash flow planning. Farmers discover the problem too late.",
    iconPath: 'M2.25 6L9 12.75l4.286-4.286a11.948 11.948 0 014.306 6.43l.776 2.898m0 0l3.182-5.511m-3.182 5.51l-5.511-3.181',
  },
  {
    title: 'No Plan to Follow',
    body: "A verbal suggestion with no roadmap, no cost estimates, no risk assessment. A recommendation that can't be acted on.",
    iconPath: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9.75m5.25-6H9.75M7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm0 2.25h.008v.008H7.5v-.008Z M6.75 3.744h-2.25a2.25 2.25 0 00-2.25 2.25v14.012a2.25 2.25 0 002.25 2.25h9a2.25 2.25 0 002.25-2.25V18.75',
  },
]

export function ProblemSection() {
  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="problem" className="bg-white py-24 sm:py-32">
      <div ref={ref} className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-12 lg:flex-row lg:items-start lg:gap-16">
          {/* LEFT — text + cards */}
          <div className="flex-1 lg:max-w-[60%]">
            {/* Label */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="mb-4 text-sm font-semibold tracking-wider text-primary-500 uppercase"
            >
              The Problem
            </motion.p>

            {/* Headline */}
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="mb-4 max-w-2xl font-display text-4xl font-normal leading-tight text-gray-900 sm:text-5xl"
            >
              Most farmers plan with
              <br />
              <span className="font-display italic text-primary-500">habit, hope, and hearsay.</span>
            </motion.h2>

            {/* Subtext */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="mb-12 max-w-xl text-lg text-gray-500 md:text-xl"
            >
              This leads to wrong crops, wasted budgets, and missed seasons —
              year after year.
            </motion.p>

            {/* Cards */}
            <div className="grid gap-5">
              {cards.map((card, i) => (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 30 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.7, delay: 0.3 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
                  className="rounded-2xl border border-gray-200 bg-gray-50/80 p-6 transition-all duration-300 hover:border-gray-300 hover:shadow-lg hover:translate-y-[-2px]"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-gold/10">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-gold">
                        <path d={card.iconPath} />
                      </svg>
                    </div>
                    <div>
                      <h3 className="mb-1.5 text-base font-bold text-gray-900">{card.title}</h3>
                      <p className="text-sm leading-relaxed text-gray-500">
                        {card.body}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Transition line */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : {}}
              transition={{ duration: 0.8, delay: 0.9 }}
              className="mt-10 text-base font-medium text-primary-500"
            >
              GrowGrid solves this — with structured intelligence, not generic AI.
            </motion.p>
          </div>

          {/* RIGHT — farmer video */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1 lg:sticky lg:top-24"
          >
            <video
              src="/videos/farmer.mp4"
              autoPlay
              loop
              muted
              playsInline
              className="w-full rounded-2xl object-cover shadow-lg"
            />
          </motion.div>
        </div>
      </div>
    </section>
  )
}
