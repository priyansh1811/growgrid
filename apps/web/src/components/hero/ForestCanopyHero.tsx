import { motion, useScroll, useTransform } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHeroParallax } from '../../hooks/useHeroParallax'

const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.9,
      delay,
      ease: [0.16, 1, 0.3, 1] as [number, number, number, number],
    },
  }),
}

const proofItems = [
  {
    value: '100+',
    label: 'crops in database',
    detail: 'Across 13 categories — vegetables, fruits, cereals, spices, flowers, and more',
  },
  {
    value: '25',
    label: 'Indian states',
    detail: 'Location-specific suitability data for climate, soil, and seasonal patterns',
  },
  {
    value: '18',
    label: 'farming practices',
    detail: 'From open-field crops to polyhouse, orchards, beekeeping, and more',
  },
  {
    value: '₹0',
    label: 'cost to you',
    detail: 'No fees, no sign-up walls. The full advisory report is completely free.',
  },
]

const signalCards = [
  {
    label: 'Crop-soil match',
    value: '94%',
    note: 'Tomato and onion rotation scored highest for red soil with drip irrigation.',
    progress: 94,
    gradient: 'linear-gradient(135deg, rgba(139,184,92,0.92), rgba(77,132,81,0.72))',
  },
  {
    label: 'Water sufficiency',
    value: '87%',
    note: 'Borwell + drip meets crop water demand for both Kharif and Rabi cycles.',
    progress: 87,
    gradient: 'linear-gradient(135deg, rgba(110,196,214,0.9), rgba(75,131,171,0.7))',
  },
  {
    label: 'Budget utilisation',
    value: '₹2.6L',
    note: 'Staged input spend across 3 months keeps ₹40K liquidity buffer intact.',
    progress: 86,
    gradient: 'linear-gradient(135deg, rgba(214,178,110,0.95), rgba(184,128,73,0.72))',
  },
]

const intelligenceCards = [
  {
    title: 'Recommended crops',
    body: 'Tomato (1.2 acres), Onion (0.8 acres) — balanced for market timing and water load.',
  },
  {
    title: 'Projected returns',
    body: 'Net margin ₹1.2L–₹1.9L across conservative to optimistic scenarios.',
  },
  {
    title: 'First 30 days',
    body: 'Soil test, drip setup, nursery procurement — full action list with week-by-week dates.',
  },
]

const productPillars = [
  'Every recommendation explained',
  'Full financial projections',
  'Month-by-month roadmap',
]

interface Particle {
  x: number
  y: number
  radius: number
  baseOpacity: number
  opacity: number
  speedY: number
  speedX: number
  color: string
}

const PARTICLE_COLORS = ['#8BB85C', '#cbb59a', '#ffffff']

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min
}

function createParticle(w: number, h: number): Particle {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)]
  const baseOpacity = rand(0.08, 0.22)

  return {
    x: rand(0, w),
    y: rand(0, h),
    radius: rand(1, 2.2),
    baseOpacity,
    opacity: baseOpacity,
    speedY: rand(-0.08, -0.2),
    speedX: rand(-0.05, 0.05),
    color,
  }
}

function PollenCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [skip, setSkip] = useState(false)

  useEffect(() => {
    if (window.innerWidth < 768) {
      setSkip(true)
      return
    }

    const canvasEl = canvasRef.current
    const wrapperEl = wrapperRef.current
    if (!canvasEl || !wrapperEl) return

    const safeCanvas = canvasEl
    const safeWrapper = wrapperEl
    const context = safeCanvas.getContext('2d')
    if (!context) return
    const safeContext = context

    let animId = 0
    let particles: Particle[] = []

    function resize() {
      const dpr = window.devicePixelRatio || 1
      const rect = safeWrapper.getBoundingClientRect()

      safeCanvas.width = rect.width * dpr
      safeCanvas.height = rect.height * dpr
      safeCanvas.style.width = `${rect.width}px`
      safeCanvas.style.height = `${rect.height}px`
      safeContext.setTransform(dpr, 0, 0, dpr, 0, 0)

      const count = rect.width < 1024 ? 18 : 34
      particles = Array.from({ length: count }, () => createParticle(rect.width, rect.height))
    }

    function draw() {
      const rect = safeWrapper.getBoundingClientRect()
      const w = rect.width
      const h = rect.height
      const dpr = window.devicePixelRatio || 1

      safeContext.clearRect(0, 0, w * dpr, h * dpr)
      safeContext.setTransform(dpr, 0, 0, dpr, 0, 0)

      for (const particle of particles) {
        particle.y += particle.speedY
        particle.x += particle.speedX
        particle.opacity =
          particle.baseOpacity + Math.sin(Date.now() * 0.0008 + particle.x) * 0.06

        if (particle.y < -10) {
          particle.y = h + 10
          particle.x = rand(0, w)
        }

        if (particle.x < -10) particle.x = w + 10
        if (particle.x > w + 10) particle.x = -10

        const alpha = Math.max(0, Math.min(1, particle.opacity))
        const alphaHex = Math.round(alpha * 255).toString(16).padStart(2, '0')
        const gradient = safeContext.createRadialGradient(
          particle.x,
          particle.y,
          0,
          particle.x,
          particle.y,
          particle.radius * 5
        )

        gradient.addColorStop(0, `${particle.color}${alphaHex}`)
        gradient.addColorStop(1, `${particle.color}00`)

        safeContext.fillStyle = gradient
        safeContext.beginPath()
        safeContext.arc(particle.x, particle.y, particle.radius * 5, 0, Math.PI * 2)
        safeContext.fill()
      }

      animId = requestAnimationFrame(draw)
    }

    resize()
    animId = requestAnimationFrame(draw)

    window.addEventListener('resize', resize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  if (skip) return null

  return (
    <div ref={wrapperRef} className="pointer-events-none absolute inset-0 z-[32]">
      <canvas ref={canvasRef} className="absolute inset-0" />
    </div>
  )
}

export function ForestCanopyHero() {
  const containerRef = useRef<HTMLDivElement>(null!)
  const navigate = useNavigate()

  const cloudParallax = useHeroParallax(containerRef, {
    speedX: -0.35,
    speedY: -0.4,
    smooth: true,
    stiffness: 42,
    damping: 18,
  })
  const forestParallax = useHeroParallax(containerRef, {
    speedY: 0.42,
    smooth: true,
    stiffness: 42,
    damping: 18,
  })
  const branchParallax = useHeroParallax(containerRef, {
    speedX: 0.18,
    speedY: 0.2,
    smooth: true,
    stiffness: 48,
    damping: 20,
  })
  const contentParallax = useHeroParallax(containerRef, {
    speedY: -0.18,
    smooth: true,
    stiffness: 50,
    damping: 22,
  })

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  })

  const contentOpacity = useTransform(scrollYProgress, [0, 0.72, 1], [1, 1, 0.48])
  const proofOpacity = useTransform(scrollYProgress, [0, 0.6, 1], [1, 0.95, 0.08])

  return (
    <section
      ref={containerRef}
      className="grain relative min-h-[100svh] overflow-hidden bg-[#050a10] text-white"
    >
      <div className="hero-grid-pattern pointer-events-none absolute inset-0 z-0 opacity-70" />

      <div className="pointer-events-none absolute inset-0 z-[1]">
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(180deg, rgba(5,10,16,0.58) 0%, rgba(5,10,16,0.22) 26%, rgba(6,18,24,0.52) 62%, rgba(5,10,16,0.96) 100%)',
          }}
        />
        <div
          className="absolute left-[12%] top-[18%] h-[420px] w-[420px] rounded-full blur-[140px]"
          style={{ background: 'rgba(97, 136, 98, 0.18)' }}
        />
        <div
          className="absolute right-[8%] top-[10%] h-[360px] w-[360px] rounded-full blur-[130px]"
          style={{ background: 'rgba(153, 123, 74, 0.18)' }}
        />
        <div
          className="absolute left-1/2 top-[44%] h-[520px] w-[720px] -translate-x-1/2 -translate-y-1/2 rounded-full blur-[120px]"
          style={{
            background:
              'radial-gradient(circle, rgba(221, 229, 203, 0.14) 0%, rgba(118, 149, 115, 0.06) 45%, transparent 72%)',
          }}
        />
      </div>

      <motion.img
        src="/images/hero/clouds-three.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="eager"
        style={{
          x: cloudParallax.x,
          y: cloudParallax.y,
          willChange: 'transform',
        }}
        className="pointer-events-none absolute left-[-10%] top-[-30%] z-[2] w-[120%] select-none mix-blend-screen opacity-55"
      />

      <motion.img
        src="/images/hero/tropical-forest.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="eager"
        style={{ y: forestParallax.y, willChange: 'transform' }}
        className="pointer-events-none absolute bottom-[-1%] left-0 z-[5] w-full select-none object-cover object-bottom opacity-[0.88]"
      />

      <motion.img
        src="/images/hero/tree-branch.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="eager"
        style={{
          x: branchParallax.x,
          y: branchParallax.y,
          willChange: 'transform',
        }}
        className="pointer-events-none absolute right-[-8%] top-[-2%] z-[8] hidden w-[44%] max-w-[620px] select-none opacity-85 lg:block"
      />

      <PollenCanvas />

      <motion.div
        style={{
          y: contentParallax.y,
          opacity: contentOpacity,
        }}
        className="relative z-30"
      >
        <div className="mx-auto flex min-h-[100svh] max-w-7xl flex-col justify-between px-4 pb-8 pt-28 sm:px-6 lg:px-8 lg:pb-10 lg:pt-32">
          <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1.02fr)_minmax(360px,0.98fr)] lg:gap-16">
            <div className="max-w-2xl">
              <motion.div
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                custom={0.05}
                className="mb-6 inline-flex items-center gap-3 rounded-full border border-white/12 bg-white/6 px-4 py-2 backdrop-blur-md"
              >
                <span className="h-2 w-2 rounded-full bg-[#b9d779] shadow-[0_0_18px_rgba(185,215,121,0.8)]" />
                <span className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/72">
                  Free AI-powered farm planning for India
                </span>
              </motion.div>

              <motion.div variants={fadeUp} initial="hidden" animate="visible" custom={0.16}>
                <h1 className="max-w-3xl font-display text-[clamp(3.5rem,8vw,5.8rem)] leading-[0.94] tracking-[-0.04em] text-white">
                  Know what to grow
                  <span className="block text-[#d6d0c4]">before you spend a rupee.</span>
                </h1>
              </motion.div>

              <motion.p
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                custom={0.28}
                className="mt-6 max-w-xl text-base leading-8 text-white/68 sm:text-lg"
              >
                Tell us about your land, water, and budget. GrowGrid analyses 86 crops across
                18 farming practices and gives you a complete plan — what to grow, what it will
                cost, and how to execute it month by month.
              </motion.p>

              <motion.div
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                custom={0.4}
                className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center"
              >
                <button
                  onClick={() => navigate('/plan')}
                  className="group inline-flex items-center gap-2 rounded-full bg-[#e8dcc7] px-7 py-3.5 text-sm font-semibold text-[#10211a] transition-transform duration-300 hover:-translate-y-0.5"
                  style={{
                    boxShadow:
                      '0 18px 45px rgba(232, 220, 199, 0.18), 0 6px 18px rgba(0, 0, 0, 0.22)',
                  }}
                >
                  Create my free farm plan
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-transform duration-300 group-hover:translate-x-1"
                  >
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </button>

                <button
                  onClick={() =>
                    document.querySelector('#how-it-works')?.scrollIntoView({ behavior: 'smooth' })
                  }
                  className="inline-flex items-center gap-2 rounded-full border border-white/14 bg-white/6 px-6 py-3.5 text-sm font-medium text-white/78 backdrop-blur-md transition-all duration-300 hover:border-white/24 hover:bg-white/10 hover:text-white"
                >
                  See how it works
                </button>
              </motion.div>

              <motion.div
                variants={fadeUp}
                initial="hidden"
                animate="visible"
                custom={0.52}
                className="mt-10 flex flex-wrap gap-3"
              >
                {productPillars.map((pillar) => (
                  <div
                    key={pillar}
                    className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/18 px-4 py-2 text-sm text-white/70 backdrop-blur-md"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-[#9dcf76]" />
                    {pillar}
                  </div>
                ))}
              </motion.div>
            </div>

            <motion.div
              variants={fadeUp}
              initial="hidden"
              animate="visible"
              custom={0.22}
              className="hero-panel surface-sheen relative overflow-hidden rounded-[32px] p-6 sm:p-7"
            >
              <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_top,rgba(232,220,199,0.18),transparent_68%)]" />

              <div className="relative z-10">
                <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#b8c4ad]">
                      Sample plan output
                    </p>
                    <h2 className="mt-3 max-w-md text-2xl font-semibold leading-tight text-white">
                      2 acres in Nashik, ₹3L budget — here's the plan.
                    </h2>
                  </div>

                  <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/60">
                    <span className="h-2 w-2 rounded-full bg-[#95d16f]" />
                    11 AI agents verified
                  </div>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  {signalCards.map((signal, index) => (
                    <motion.div
                      key={signal.label}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.65,
                        delay: 0.42 + index * 0.08,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                      className="rounded-2xl border border-white/10 bg-white/[0.04] p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-[0.24em] text-white/38">
                            {signal.label}
                          </p>
                          <p className="mt-2 text-2xl font-semibold text-white">{signal.value}</p>
                        </div>
                        <div
                          className="h-2.5 w-2.5 rounded-full"
                          style={{ background: signal.gradient }}
                        />
                      </div>

                      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
                        <motion.div
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: signal.progress / 100 }}
                          transition={{
                            duration: 0.9,
                            delay: 0.52 + index * 0.08,
                            ease: [0.16, 1, 0.3, 1],
                          }}
                          className="h-full origin-left rounded-full"
                          style={{ background: signal.gradient }}
                        />
                      </div>

                      <p className="mt-3 text-sm leading-6 text-white/55">{signal.note}</p>
                    </motion.div>
                  ))}
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  {intelligenceCards.map((card, index) => (
                    <motion.div
                      key={card.title}
                      initial={{ opacity: 0, y: 22 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.65,
                        delay: 0.66 + index * 0.08,
                        ease: [0.16, 1, 0.3, 1],
                      }}
                      className="rounded-2xl border border-white/10 bg-black/16 p-4"
                    >
                      <p className="text-sm font-semibold text-white">{card.title}</p>
                      <p className="mt-2 text-sm leading-6 text-white/50">{card.body}</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>

          <motion.div
            style={{ opacity: proofOpacity }}
            className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4"
          >
            {proofItems.map((item, index) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.7,
                  delay: 0.56 + index * 0.07,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="hero-panel surface-sheen rounded-[28px] p-5"
              >
                <p className="text-[11px] uppercase tracking-[0.3em] text-[#b8c4ad]">GrowGrid in numbers</p>
                <p className="mt-4 text-3xl font-semibold text-white">{item.value}</p>
                <p className="mt-2 text-sm font-medium uppercase tracking-[0.18em] text-white/72">
                  {item.label}
                </p>
                <p className="mt-4 text-sm leading-6 text-white/50">{item.detail}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.div>
    </section>
  )
}
