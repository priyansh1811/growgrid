import { motion, useScroll, useTransform } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHeroParallax } from '../../hooks/useHeroParallax'

/* ------------------------------------------------------------------ */
/*  Animation variants                                                 */
/* ------------------------------------------------------------------ */

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] as [number, number, number, number], delay },
  }),
}

/* ------------------------------------------------------------------ */
/*  Pollen / dust particle system (canvas)                             */
/* ------------------------------------------------------------------ */

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

const PARTICLE_COLORS = ['#8BB85C', '#c8a97e', '#ffffff']

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min
}

function createParticle(w: number, h: number): Particle {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)]
  const baseOpacity = rand(0.1, 0.35)
  return {
    x: rand(0, w),
    y: rand(0, h),
    radius: rand(1, 2.5),
    baseOpacity,
    opacity: baseOpacity,
    speedY: rand(-0.08, -0.25),
    speedX: rand(-0.06, 0.06),
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

    const canvas = canvasRef.current
    const wrapper = wrapperRef.current
    if (!canvas || !wrapper) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId = 0
    let particles: Particle[] = []

    function resize() {
      const dpr = window.devicePixelRatio || 1
      const rect = wrapper!.getBoundingClientRect()
      canvas!.width = rect.width * dpr
      canvas!.height = rect.height * dpr
      canvas!.style.width = `${rect.width}px`
      canvas!.style.height = `${rect.height}px`
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)

      const count = rect.width < 1024 ? 15 : 30
      particles = Array.from({ length: count }, () =>
        createParticle(rect.width, rect.height)
      )
    }

    function draw() {
      const rect = wrapper!.getBoundingClientRect()
      const w = rect.width
      const h = rect.height
      const dpr = window.devicePixelRatio || 1

      ctx!.clearRect(0, 0, w * dpr, h * dpr)
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)

      for (const p of particles) {
        p.y += p.speedY
        p.x += p.speedX
        p.opacity = p.baseOpacity + Math.sin(Date.now() * 0.0008 + p.x) * 0.08

        if (p.y < -10) {
          p.y = h + 10
          p.x = rand(0, w)
        }
        if (p.x < -10) p.x = w + 10
        if (p.x > w + 10) p.x = -10

        const alpha = Math.max(0, Math.min(1, p.opacity))
        const alphaHex = Math.round(alpha * 255).toString(16).padStart(2, '0')
        const gradient = ctx!.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 5)
        gradient.addColorStop(0, `${p.color}${alphaHex}`)
        gradient.addColorStop(1, `${p.color}00`)

        ctx!.fillStyle = gradient
        ctx!.beginPath()
        ctx!.arc(p.x, p.y, p.radius * 5, 0, Math.PI * 2)
        ctx!.fill()
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
    <div ref={wrapperRef} className="pointer-events-none absolute inset-0 z-[41]">
      <canvas ref={canvasRef} className="absolute inset-0" />
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  3D text-shadow for the GrowGrid heading                            */
/* ------------------------------------------------------------------ */

const growgridTextShadow = [
  // Soft depth — refined layered descent
  '0 1px 2px rgba(0,0,0,0.2)',
  '0 4px 12px rgba(0,0,0,0.18)',
  '0 10px 30px rgba(0,0,0,0.14)',
  // Diffused ambient shadow for grounding
  '0 20px 50px rgba(0,0,0,0.10)',
  // Very subtle warm glow
  '0 0 60px rgba(205,197,180,0.05)',
  '0 0 100px rgba(184,196,173,0.04)',
].join(', ')

/* ------------------------------------------------------------------ */
/*  Leaf decoration positions (behind text)                            */
/* ------------------------------------------------------------------ */

const leafBlobs = [
  { top: '35%', left: '12%', w: 260, h: 180, color: 'rgba(74,140,98,0.10)', blur: 70 },
  { top: '40%', right: '10%', w: 280, h: 160, color: 'rgba(58,112,80,0.08)', blur: 80 },
  { top: '52%', left: '25%', w: 200, h: 130, color: 'rgba(107,166,126,0.07)', blur: 60 },
  { top: '44%', right: '22%', w: 220, h: 150, color: 'rgba(74,140,98,0.06)', blur: 90 },
]

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ForestCanopyHero() {
  const containerRef = useRef<HTMLDivElement>(null!)
  const navigate = useNavigate()

  const forestParallax = useHeroParallax(containerRef, { speedY: 0.5 })
  const leafParallax = useHeroParallax(containerRef, { speedY: 0.6 })
  const headingParallax = useHeroParallax(containerRef, { speedY: -0.5, smooth: true, stiffness: 50, damping: 22 })

  // Tree branch scrolls down as user scrolls past hero
  const { scrollYProgress: branchScrollProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  })
  const branchY = useTransform(branchScrollProgress, [0, 1.2], [0, 400])

  return (
    <section
      ref={containerRef}
      className="grain relative h-screen overflow-hidden"
      style={{ backgroundColor: '#0a0f0a' }}
    >
      {/* Radial canopy glow — dramatic sunlight through canopy */}
      <div className="pointer-events-none absolute inset-0 z-0">
        {/* Primary warm light beam */}
        <div
          className="absolute left-1/2 top-[42%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            width: '1000px',
            height: '600px',
            background: 'radial-gradient(ellipse, rgba(200,220,180,0.07) 0%, rgba(107,166,126,0.03) 40%, transparent 70%)',
          }}
        />
        {/* Secondary accent glow */}
        <div
          className="absolute left-[45%] top-[38%] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            width: '600px',
            height: '400px',
            background: 'radial-gradient(ellipse, rgba(107,166,126,0.05) 0%, transparent 60%)',
          }}
        />
        {/* Vignette — darkens edges */}
        <div
          className="absolute inset-0"
          style={{
            background: 'radial-gradient(ellipse 70% 60% at 50% 45%, transparent 40%, rgba(10,15,10,0.6) 100%)',
          }}
        />
      </div>

      {/* Tropical forest — bottom/sides frame (z-10) */}
      <motion.img
        src="/images/hero/tropical-forest.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="eager"
        style={{ y: forestParallax.y, willChange: 'transform' }}
        className="pointer-events-none absolute bottom-[0] left-0 z-10 w-full select-none object-cover object-bottom"
      />

      {/* Leaf decorations behind text (z-20) */}
      <motion.div
        className="pointer-events-none absolute inset-0 z-20"
        style={{ y: leafParallax.y }}
      >
        {leafBlobs.map((blob, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              top: blob.top,
              left: 'left' in blob ? blob.left : undefined,
              right: 'right' in blob ? blob.right : undefined,
              width: blob.w,
              height: blob.h,
              background: `radial-gradient(ellipse, ${blob.color}, transparent 70%)`,
              filter: `blur(${blob.blur}px)`,
            }}
          />
        ))}
      </motion.div>

      {/* Main content — heading + tagline + CTAs (z-30) */}
      <motion.div
        style={{ y: headingParallax.y }}
        className="relative z-30 flex h-full flex-col items-center justify-center px-4 text-center"
      >

        {/* ── GROWGRID 3D HEADING ── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92, filter: 'blur(12px)' }}
          animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
          className="relative"
        >
          {/* Breathing ambient glow behind title — warm/sage, very subtle */}
          <div
            className="hero-ambient-glow pointer-events-none absolute -inset-x-40 -inset-y-20"
            style={{
              background: 'radial-gradient(ellipse 70% 60% at 50% 55%, rgba(205,197,180,0.08) 0%, rgba(184,196,173,0.03) 50%, transparent 80%)',
              filter: 'blur(15px)',
            }}
          />

          {/* Layer 1: Shadow text (visible color so text-shadow works) */}
          <h1
            className="hero-title-3d font-display leading-none"
            style={{
              fontSize: 'clamp(3rem, 9vw, 7rem)',
              fontWeight: 600,
              letterSpacing: '0.04em',
            }}
            aria-label="GrowGrid"
          >
            <span className="hero-title-3d-shadow" style={{ textShadow: growgridTextShadow }}>
              GrowGrid
            </span>
            {/* Layer 2: Animated gradient fill (overlaid exactly on top) */}
            <span className="hero-title-3d-gradient" aria-hidden="true">
              GrowGrid
            </span>
          </h1>
        </motion.div>

        {/* ── DECORATIVE DIVIDER ── */}
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ duration: 1, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mt-6 flex origin-center items-center gap-3"
        >
          <div className="h-px w-16 sm:w-24" style={{ background: 'linear-gradient(90deg, transparent, rgba(205,197,180,0.35))' }} />
          <div className="h-1.5 w-1.5 rotate-45 rounded-sm" style={{ backgroundColor: 'rgba(205,197,180,0.45)' }} />
          <div className="h-px w-16 sm:w-24" style={{ background: 'linear-gradient(90deg, rgba(205,197,180,0.35), transparent)' }} />
        </motion.div>

        {/* ── TAGLINE ── */}
        <motion.p
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.6}
          className="mx-auto mt-6 max-w-xl rounded-full px-6 py-2.5 text-base leading-relaxed tracking-wide text-white/80 backdrop-blur-md sm:text-lg"
          style={{
            fontStyle: 'italic',
            background: 'linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03))',
            border: '1px solid rgba(255,255,255,0.10)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
          }}
        >
          Where agriculture meets intelligence, strategy, and profitability.
        </motion.p>

        {/* ── CTAs ── */}
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0.95}
          className="mt-9 flex flex-col items-center gap-4 sm:flex-row"
        >
          {/* Primary — solid gold */}
          <button
            onClick={() => navigate('/plan')}
            className="group relative overflow-hidden rounded-full bg-accent-gold px-10 py-4 text-lg font-semibold text-forest transition-all duration-300 hover:bg-accent-gold-light hover:translate-y-[-1px]"
            style={{
              boxShadow: '0 8px 24px rgba(200,149,108,0.3), 0 2px 8px rgba(0,0,0,0.2)',
            }}
          >
            <span className="relative z-10 flex items-center gap-2">
              Plan My Farm
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-hover:translate-x-1">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </span>
          </button>

          {/* Secondary — frosted glass */}
          <button
            onClick={() =>
              document.querySelector('#how-it-works')?.scrollIntoView({ behavior: 'smooth' })
            }
            className="group relative overflow-hidden rounded-full px-9 py-4 text-lg font-medium text-white/70 transition-all duration-300 hover:text-white/90"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))',
              border: '1px solid rgba(255,255,255,0.12)',
              boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
            }}
          >
            <span className="relative z-10">See How It Works</span>
            <span className="pointer-events-none absolute inset-0 rounded-full opacity-0 transition-all duration-300 group-hover:opacity-100"
              style={{
                background: 'linear-gradient(135deg, rgba(107,166,126,0.08), rgba(255,255,255,0.04))',
                border: '1px solid rgba(107,166,126,0.25)',
              }}
            />
          </button>
        </motion.div>

        {/* ── SCROLL INDICATOR ── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.8, duration: 1 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-scroll-indicator"
        >
          <div className="flex flex-col items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-[0.25em] text-white/25">Scroll</span>
            <div className="flex h-8 w-5 items-start justify-center rounded-full border border-white/15 p-1.5">
              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                className="h-1.5 w-1 rounded-full bg-primary-400/50"
              />
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Tree branch — foreground canopy top (z-40), scrolls down with user */}
      <motion.img
        src="/images/hero/tree-branch.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        loading="eager"
        style={{ y: branchY, willChange: 'transform' }}
        className="pointer-events-none absolute left-[399px] -top-[70px] z-40 w-[40%] select-none object-cover object-top"
      />

      {/* Pollen / dust particles */}
      <PollenCanvas />
    </section>
  )
}
