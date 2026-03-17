import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const personas = [
  {
    title: 'First-Time Farmers',
    body: "Never farmed before? GrowGrid asks 9 simple questions about your land and budget, then gives you a step-by-step plan — which crops to grow, how much to spend, and exactly what to do each month. No agriculture background needed.",
    tags: ['Open Field', 'Drip Horticulture', 'Step-by-Step Roadmap'],
    iconPath: 'M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z',
  },
  {
    title: 'Landowners & Investors',
    body: 'Want to know if farming your land makes financial sense? GrowGrid produces a 3-scenario financial model (conservative, base, optimistic) with projected revenue, costs, and break-even — based on your actual land, water, and budget.',
    tags: ['ROI Analysis', '3-Scenario P&L', 'Break-Even Projection'],
    iconPath: 'M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 0h.008v.008h-.008v-.008z',
  },
  {
    title: 'Agri Consultants',
    body: 'Generate professional 17-section advisory reports for your clients in minutes. Every recommendation is scored, explained, and verified — structured enough to present to banks or government agencies.',
    tags: ['17-Section Report', 'Agronomist Verified', 'Govt Scheme Matching'],
    iconPath: 'M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z',
  },
]

export function ForWhomSection() {
  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="for-whom" className="bg-cream py-24 sm:py-32">
      <div ref={ref} className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-4 text-sm font-semibold tracking-wider text-primary-500 uppercase"
        >
          Who It's For
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-16 font-display text-4xl font-normal leading-tight text-gray-900 sm:text-5xl"
        >
          Built for anyone making
          <br />
          <span className="font-display italic text-primary-500">a farming decision.</span>
        </motion.h2>

        <div className="grid gap-6 md:grid-cols-3">
          {personas.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.7, delay: 0.2 + i * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="group rounded-2xl border border-gray-200 bg-white p-8 transition-all duration-300 hover:border-gray-300 hover:shadow-lg hover:translate-y-[-2px]"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-accent-gold/10">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-accent-gold">
                  <path d={p.iconPath} />
                </svg>
              </div>
              <h3 className="mb-3 text-xl font-bold text-gray-900">{p.title}</h3>
              <p className="mb-6 text-sm leading-relaxed text-gray-500">
                {p.body}
              </p>
              <div className="flex flex-wrap gap-2">
                {p.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-[11px] font-medium text-primary-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
