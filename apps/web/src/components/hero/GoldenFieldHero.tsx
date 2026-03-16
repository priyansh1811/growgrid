import { motion } from 'framer-motion'
import { useRef } from 'react'
import { useCountUp } from '../../hooks/useCountUp'
import { useHeroParallax } from '../../hooks/useHeroParallax'

/* ------------------------------------------------------------------ */
/*  Stats data                                                         */
/* ------------------------------------------------------------------ */

const stats = [
  { target: 1200, suffix: '+', prefix: '', label: 'Plans Generated', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { target: 14, suffix: '', prefix: '', label: 'States Covered', icon: 'M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z' },
  { target: 11, suffix: '', prefix: '', label: 'AI Agents', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { target: 0, suffix: '', prefix: '₹', label: 'Consulting Fee', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
]

/* ------------------------------------------------------------------ */
/*  Stat metric with count-up animation + glass card                   */
/* ------------------------------------------------------------------ */

function StatMetric({
  target,
  prefix,
  suffix,
  label,
  icon,
  delay,
}: {
  target: number
  prefix: string
  suffix: string
  label: string
  icon: string
  delay: number
}) {
  const { ref, count } = useCountUp(target, 2)

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className="stat-glass group flex flex-col items-center rounded-2xl px-4 py-6 text-center transition-all duration-300 hover:border-white/20 sm:px-6 sm:py-8"
    >
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-white/5 transition-colors group-hover:bg-primary-500/10">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(107,166,126,0.7)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d={icon} />
        </svg>
      </div>
      <p className="text-3xl font-bold text-white sm:text-4xl md:text-5xl">
        {prefix}
        {count}
        {suffix}
      </p>
      <p className="mt-2 text-[11px] font-medium uppercase tracking-wider text-white/55 sm:text-xs">
        {label}
      </p>
    </motion.div>
  )
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function GoldenFieldHero() {
  const containerRef = useRef<HTMLDivElement>(null!)

  const cloudsThreeParallax = useHeroParallax(containerRef, {
    speedX: -0.6,
    speedY: -0.8,
  })
  const cloudsTwoParallax = useHeroParallax(containerRef, {
    speedX: 0.6,
    speedY: -0.9,
  })
  const greenlandParallax = useHeroParallax(containerRef, { speedY: 0.8 })

  return (
    <section
      ref={containerRef}
      className="grain relative h-screen overflow-hidden"
      style={{
        background:
          'linear-gradient(to bottom, #0a0f0a 0%, #0c1a0e 20%, #142a16 40%, #1e3e1e 60%, #2d5a2a 80%, #3a6a35 100%)',
      }}
    >
      {/* Clouds three — upper area, drift LEFT (z-10) */}
      <motion.img
        src="/images/hero/clouds-three.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="lazy"
        style={{
          x: cloudsThreeParallax.x,
          y: cloudsThreeParallax.y,
          willChange: 'transform',
        }}
        className="pointer-events-none absolute left-[-5%] top-[-35%] z-10 w-[110%] select-none mix-blend-screen opacity-90 md:animate-none max-md:animate-[cloud-drift-left_12s_ease-in-out_infinite]"
      />

      {/* Clouds two — middle area, drift RIGHT (z-15) */}
      <motion.img
        src="/images/hero/clouds-two.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="lazy"
        style={{
          x: cloudsTwoParallax.x,
          y: cloudsTwoParallax.y,
          willChange: 'transform',
        }}
        className="pointer-events-none absolute right-[-5%] top-[-45%] z-[15] w-[110%] select-none mix-blend-screen opacity-85 md:animate-none max-md:animate-[cloud-drift-right_14s_ease-in-out_infinite]"
      />

      {/* Stats content (z-20) */}
      <div className="relative z-20 flex h-full flex-col items-center justify-center px-4">
        {/* Section headline */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mb-3 text-center"
        >
          <h2 className="font-display text-3xl font-normal leading-tight text-white sm:text-4xl md:text-5xl">
            Trusted across{' '}
            <span
              style={{
                color: 'transparent',
                backgroundImage: 'linear-gradient(90deg, #93C5A4, #6BA67E, #4A8C62)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
              }}
            >
              Indian farmland
            </span>
          </h2>
        </motion.div>

        {/* Divider */}
        <motion.div
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-4 h-px w-24 origin-center"
          style={{ background: 'linear-gradient(90deg, transparent, rgba(107,166,126,0.45), transparent)' }}
        />

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mb-10 max-w-xl text-center text-sm leading-relaxed text-white/55 sm:text-base"
        >
          An explainable, multi-agent system that recommends what to grow, why,
          and how — backed by data, verified by AI.
        </motion.p>

        {/* Stats row */}
        <div className="grid w-full max-w-4xl grid-cols-2 gap-4 sm:gap-5 lg:grid-cols-4">
          {stats.map((s, i) => (
            <StatMetric key={s.label} {...s} delay={0.1 + i * 0.1} />
          ))}
        </div>
      </div>

      {/* Greenland — bottom anchor (z-5) */}
      <motion.img
        src="/images/hero/greenland.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="lazy"
        style={{ y: greenlandParallax.y, willChange: 'transform' }}
        className="pointer-events-none absolute bottom-0 left-0 z-[5] w-full select-none object-cover object-bottom"
      />

      {/* Subtle glow behind stats */}
      <div className="pointer-events-none absolute inset-0 z-[1]">
        <div
          className="absolute left-1/2 top-[45%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            width: '700px',
            height: '400px',
            background:
              'radial-gradient(ellipse, rgba(107,166,126,0.05) 0%, transparent 70%)',
          }}
        />
      </div>

      {/* Gradient bridge to next section */}
      <div
        className="absolute bottom-0 left-0 z-[25] h-32 w-full"
        style={{
          background: 'linear-gradient(to bottom, transparent, #FFFFFF)',
        }}
      />
    </section>
  )
}
