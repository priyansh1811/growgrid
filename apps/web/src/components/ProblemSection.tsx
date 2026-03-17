import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const cards = [
  {
    title: 'Wrong crop, wrong season',
    body: 'Farmers often grow what their neighbour grew last year — without checking whether their own soil, water supply, or planting window actually supports that crop.',
    iconPath:
      'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z',
  },
  {
    title: 'Budget mismatches',
    body: "Money goes into seeds and inputs before anyone checks whether the budget can sustain the full crop cycle. By mid-season, funds run out and options disappear.",
    iconPath:
      'M2.25 6L9 12.75l4.286-4.286a11.948 11.948 0 014.306 6.43l.776 2.898m0 0l3.182-5.511m-3.182 5.51l-5.511-3.181',
  },
  {
    title: 'No roadmap to execute',
    body: 'Even good crop advice is useless without a schedule — when to prepare soil, when to plant, when to apply inputs, and when to harvest. Without a roadmap, farmers improvise under pressure.',
    iconPath:
      'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12H9.75m5.25-6H9.75M7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm0 2.25h.008v.008H7.5v-.008Z M6.75 3.744h-2.25a2.25 2.25 0 00-2.25 2.25v14.012a2.25 2.25 0 002.25 2.25h9a2.25 2.25 0 002.25-2.25V18.75',
  },
]


export function ProblemSection() {
  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="problem" className="relative overflow-hidden bg-[#f6f1e8] py-24 sm:py-32">
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-[6%] top-[10%] h-72 w-72 rounded-full blur-[120px]"
          style={{ background: 'rgba(189, 173, 136, 0.2)' }}
        />
        <div
          className="absolute right-[4%] top-[18%] h-80 w-80 rounded-full blur-[120px]"
          style={{ background: 'rgba(126, 154, 118, 0.18)' }}
        />
      </div>

      <div ref={ref} className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.92fr)_minmax(340px,0.88fr)] lg:gap-14">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 18 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="text-[11px] font-semibold uppercase tracking-[0.32em] text-[#5d745b]"
            >
              The problem
            </motion.p>

            <div className="mt-5 flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
              <motion.h2
                initial={{ opacity: 0, y: 22 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.75, delay: 0.08, ease: [0.16, 1, 0.3, 1] }}
                className="max-w-2xl font-display text-4xl leading-tight tracking-[-0.04em] text-[#17241c] sm:text-5xl lg:text-6xl"
              >
                Most farms plan by copying their neighbours.
              </motion.h2>

              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.75, delay: 0.16, ease: [0.16, 1, 0.3, 1] }}
                className="surface-light max-w-sm rounded-[28px] p-5"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#617261]">
                  The core issue
                </p>
                <p className="mt-3 text-sm leading-7 text-[#455447]">
                  The problem isn't hard work — it's that no affordable tool combines crop
                  science, financial planning, and an execution roadmap into one plan before
                  you start spending.
                </p>
              </motion.div>
            </div>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.75, delay: 0.18, ease: [0.16, 1, 0.3, 1] }}
              className="mt-8 max-w-2xl text-base leading-8 text-[#455447] sm:text-lg"
            >
              A wrong crop choice doesn't just hurt yield. It drains your budget, wastes the
              season's narrow window, and leaves no backup plan when weather or markets shift.
            </motion.p>

            <div className="mt-10 grid gap-4">
              {cards.map((card, index) => (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 26 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{
                    duration: 0.72,
                    delay: 0.24 + index * 0.08,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className="surface-light rounded-[28px] p-6"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#eef4e8] text-[#4e6f4b]">
                      <svg
                        width="22"
                        height="22"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d={card.iconPath} />
                      </svg>
                    </div>

                    <div className="flex-1">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <h3 className="text-xl font-semibold tracking-[-0.02em] text-[#17241c]">
                          {card.title}
                        </h3>
                        <span className="text-xs font-semibold uppercase tracking-[0.24em] text-[#6a7b68]">
                          0{index + 1}
                        </span>
                      </div>
                      <p className="mt-3 max-w-2xl text-sm leading-7 text-[#556455] sm:text-base">
                        {card.body}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

          </div>

          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.75, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="lg:sticky lg:top-24"
          >
            <div className="surface-light rounded-[32px] p-4 sm:p-5">
              <div className="overflow-hidden rounded-[28px] border border-black/6 bg-[#0f1713] shadow-[0_24px_60px_rgba(7,12,9,0.18)]">
                <div className="relative flex items-center justify-center bg-[#0a110d] h-[360px] sm:h-[440px] overflow-hidden">
                  <video
                    src="/videos/farmer.mp4"
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="h-full w-full object-cover object-center"
                  />

                  <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(15,23,19,0.08),rgba(15,23,19,0.68))]" />

                  <div className="absolute inset-x-0 bottom-0 p-5 text-white">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/60">
                      Reality on the ground
                    </p>
                    <p className="mt-2 max-w-md text-2xl font-semibold leading-tight tracking-[-0.03em]">
                      By the time a farmer gets professional advice, the budget is spent and the season is halfway over.
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 border-t border-white/10 bg-[#101915] p-4 sm:grid-cols-[1.1fr_0.9fr]">
                  <div className="overflow-hidden rounded-2xl border border-white/10">
                    <video
                      src="/videos/Agri-field.mp4"
                      autoPlay
                      loop
                      muted
                      playsInline
                      className="h-full w-full object-cover"
                    />
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-white">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/50">
                      Structural issue
                    </p>
                    <div className="mt-4 space-y-4">
                      <div>
                        <p className="text-3xl font-semibold tracking-[-0.04em] text-[#f1eadf]">
                          Late
                        </p>
                        <p className="mt-1 text-sm leading-6 text-white/62">
                          Most planning starts after land prep and seed purchase — the biggest
                          decisions — are already locked in.
                        </p>
                      </div>
                      <div className="h-px bg-white/10" />
                      <div>
                        <p className="text-3xl font-semibold tracking-[-0.04em] text-[#f1eadf]">
                          Generic
                        </p>
                        <p className="mt-1 text-sm leading-6 text-white/62">
                          Generic advice doesn’t account for your specific budget, water source,
                          labour availability, or risk tolerance — all at once.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <p className="mt-5 text-sm font-medium text-[#4b634d]">
                GrowGrid gives you a complete plan — tailored to your land, budget, and water —
                before you spend your first rupee.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
