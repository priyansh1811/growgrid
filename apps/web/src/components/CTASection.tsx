import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

export function CTASection() {
  const navigate = useNavigate()

  return (
    <section
      className="grain relative flex min-h-[80vh] items-center justify-center overflow-hidden"
      style={{
        background:
          'linear-gradient(to bottom, #F5F2EC 0%, #3a3020 25%, #2a1f0a 50%, #8a6a30 80%, #c9a050 100%)',
      }}
    >
      {/* Warm ambient glows */}
      <div className="pointer-events-none absolute inset-0">
        <div
          className="absolute left-1/2 top-[40%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            width: '800px',
            height: '500px',
            background: 'radial-gradient(ellipse, rgba(200,149,108,0.08) 0%, transparent 70%)',
          }}
        />
        <div className="absolute -left-32 -top-32 h-[300px] w-[300px] rounded-full blur-[120px]" style={{ background: 'rgba(200,149,108,0.06)' }} />
        <div className="absolute -bottom-32 -right-32 h-[300px] w-[300px] rounded-full blur-[120px]" style={{ background: 'rgba(200,149,108,0.06)' }} />
      </div>

      {/* Content */}
      <div className="relative z-20 mx-auto max-w-3xl px-4 text-center">
        {/* Decorative divider */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          whileInView={{ opacity: 1, scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mx-auto mb-10 flex origin-center items-center gap-3"
        >
          <div className="h-px w-12 sm:w-20" style={{ background: 'linear-gradient(90deg, transparent, rgba(200,149,108,0.4))' }} />
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(200,149,108,0.6)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75" />
          </svg>
          <div className="h-px w-12 sm:w-20" style={{ background: 'linear-gradient(90deg, rgba(200,149,108,0.4), transparent)' }} />
        </motion.div>

        {/* Headline */}
        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mb-6 font-display text-5xl font-normal leading-tight text-white sm:text-6xl md:text-7xl"
        >
          Your best farm plan
          <br />
          starts{' '}
          <span
            className="font-display italic"
            style={{
              color: 'transparent',
              backgroundImage: 'linear-gradient(90deg, #D4A574, #C8956C, #B07D54)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
            }}
          >
            here.
          </span>
        </motion.h2>

        {/* Sub */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto mb-10 max-w-2xl text-lg text-white/60 md:text-xl"
        >
          Join farmers and landowners across 14 states making smarter,
          data-driven decisions with GrowGrid AI.
        </motion.p>

        {/* Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center"
        >
          <button
            onClick={() => navigate('/plan')}
            className="rounded-full bg-accent-gold px-10 py-5 text-lg font-semibold text-forest transition-all duration-300 hover:bg-accent-gold-light hover:translate-y-[-1px] sm:text-xl"
            style={{
              boxShadow: '0 8px 24px rgba(200,149,108,0.25), 0 4px 12px rgba(0,0,0,0.2)',
            }}
          >
            Get My Free Farm Plan
          </button>
          <button
            onClick={() =>
              document.querySelector('#agents')?.scrollIntoView({ behavior: 'smooth' })
            }
            className="rounded-full border border-white/15 px-10 py-5 text-lg font-medium text-white/70 transition-all duration-300 hover:border-white/30 hover:bg-white/5 hover:text-white/90"
          >
            Explore the Agent Pipeline
          </button>
        </motion.div>
      </div>

      {/* Wheat field — bottom anchor */}
      <img
        src="/images/hero/wheat-field.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="lazy"
        className="pointer-events-none absolute bottom-0 left-0 z-10 w-full select-none object-cover object-bottom"
      />

      {/* Top gradient bridge from previous section */}
      <div
        className="absolute left-0 top-0 z-[5] h-24 w-full"
        style={{
          background: 'linear-gradient(to bottom, #F5F2EC, transparent)',
        }}
      />
    </section>
  )
}
