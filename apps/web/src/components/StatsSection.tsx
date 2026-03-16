import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { useCountUp } from '../hooks/useCountUp'

function StatCard({
  target,
  prefix,
  suffix,
  label,
  delay,
}: {
  target: number
  prefix?: string
  suffix?: string
  label: string
  delay: number
}) {
  const { ref, count } = useCountUp(target, 2)

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay }}
      className="rounded-3xl border border-white/10 bg-card-dark p-8 text-center sm:p-10"
    >
      <p className="text-5xl font-black text-white sm:text-6xl md:text-7xl">
        {prefix}
        {count}
        {suffix}
      </p>
      <p className="mt-3 text-sm leading-snug text-text-muted-dark">{label}</p>
    </motion.div>
  )
}

export function StatsSection() {
  const { ref, inView } = useInView({ threshold: 0.15, triggerOnce: true })

  return (
    <section id="impact" className="bg-forest py-20 sm:py-24">
      <div ref={ref} className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-12 text-center text-4xl font-black leading-tight text-white sm:text-5xl"
        >
          Built to make Indian farming
          <br />
          <span className="italic text-emerald-400">more profitable.</span>
        </motion.h2>

        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard target={34} prefix="+" suffix="%" label="Higher projected ROI vs. unplanned conventional farming" delay={0.1} />
          <StatCard target={11} label="Specialist AI agents working in sequence on your plan" delay={0.2} />
          <StatCard target={17} label="Report sections in every complete farm advisory" delay={0.3} />
          <StatCard target={0} prefix="₹" label="Consulting fee — vs. ₹5,000–₹25,000 charged by private agri-consultants" delay={0.4} />
        </div>
      </div>
    </section>
  )
}
