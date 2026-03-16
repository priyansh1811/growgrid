import { useEffect, useRef, useState } from 'react'
import { useIntersectionFade } from '../../hooks/useIntersectionFade'

interface LandingHeroProps {
  formRef: React.RefObject<HTMLDivElement>
}

/* ------------------------------------------------------------------ */
/*  Particle system                                                    */
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

const COLORS = ['#a3e635', '#c8a97e']

function rand(min: number, max: number) {
  return Math.random() * (max - min) + min
}

function createParticle(w: number, h: number): Particle {
  const color = COLORS[Math.floor(Math.random() * COLORS.length)]
  const baseOpacity = rand(0.2, 0.7)
  return {
    x: rand(0, w),
    y: rand(0, h),
    radius: rand(1, 3),
    baseOpacity,
    opacity: baseOpacity,
    speedY: rand(-0.15, -0.5),
    speedX: rand(-0.1, 0.1),
    color,
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function LandingHero({ formRef }: LandingHeroProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [ctaOffset, setCtaOffset] = useState({ x: 0, y: 0 })
  const supportsHover = useRef(true)

  // Check hover capability once
  useEffect(() => {
    supportsHover.current = window.matchMedia('(hover: hover)').matches
  }, [])

  /* ---------- canvas particles ---------- */
  useEffect(() => {
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
      ctx!.scale(dpr, dpr)

      // Responsive particle count
      const count = rect.width < 640 ? 40 : rect.width < 1024 ? 60 : 80
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
        // Move
        p.y += p.speedY
        p.x += p.speedX

        // Gentle opacity flicker
        p.opacity = p.baseOpacity + Math.sin(Date.now() * 0.001 + p.x) * 0.1

        // Reset if off-screen
        if (p.y < -10) {
          p.y = h + 10
          p.x = rand(0, w)
        }
        if (p.x < -10) p.x = w + 10
        if (p.x > w + 10) p.x = -10

        // Draw glow
        const alpha = Math.max(0, Math.min(1, p.opacity))
        const alphaHex = Math.round(alpha * 255)
          .toString(16)
          .padStart(2, '0')
        const gradient = ctx!.createRadialGradient(
          p.x, p.y, 0,
          p.x, p.y, p.radius * 5
        )
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

  /* ---------- intersection observers for about cards ---------- */
  const [card1Ref, card1Visible] = useIntersectionFade()
  const [card2Ref, card2Visible] = useIntersectionFade()
  const [card3Ref, card3Visible] = useIntersectionFade()

  /* ---------- magnetic CTA button ---------- */
  const handleCtaMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (!supportsHover.current) return
    const rect = e.currentTarget.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = (e.clientX - cx) * 0.15
    const dy = (e.clientY - cy) * 0.15
    setCtaOffset({
      x: Math.max(-8, Math.min(8, dx)),
      y: Math.max(-8, Math.min(8, dy)),
    })
  }

  const handleCtaMouseLeave = () => setCtaOffset({ x: 0, y: 0 })

  const scrollToForm = () => {
    formRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /* ---------- render ---------- */
  return (
    <div ref={wrapperRef} className="relative overflow-hidden bg-hero-bg">
      {/* Particle canvas */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0 z-0"
      />

      {/* ====== HERO SECTION ====== */}
      <section className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 text-center">
        {/* Top badge */}
        <div className="animate-hero-tagline mb-8 inline-flex items-center gap-2 rounded-full border border-hero-lime/20 bg-hero-lime/5 px-5 py-2">
          <span className="h-2 w-2 rounded-full bg-hero-lime shadow-[0_0_8px_rgba(163,230,53,0.6)]" />
          <span className="text-xs font-medium tracking-widest uppercase text-hero-lime">
            AI-Powered Agriculture
          </span>
        </div>

        {/* Title */}
        <h1 className="animate-hero-title animate-hero-glow font-display text-6xl leading-none tracking-tight text-hero-text sm:text-7xl md:text-8xl lg:text-9xl">
          GrowGrid
        </h1>

        {/* Tagline */}
        <p className="animate-hero-tagline mt-6 max-w-lg text-base leading-relaxed text-hero-text-muted sm:text-lg md:text-xl">
          Precision farming intelligence. From soil to strategy.
        </p>

        {/* CTA */}
        <button
          onClick={scrollToForm}
          onMouseMove={handleCtaMouseMove}
          onMouseLeave={handleCtaMouseLeave}
          style={{
            transform: `translate(${ctaOffset.x}px, ${ctaOffset.y}px)`,
          }}
          className="animate-hero-cta mt-10 rounded-full bg-hero-lime px-8 py-4 text-sm font-semibold text-hero-bg transition-all duration-200 hover:shadow-[0_0_40px_rgba(163,230,53,0.35)] active:scale-95"
        >
          Get Your Free Farm Consulting Report&ensp;&rarr;
        </button>

        {/* Scroll indicator */}
        <div className="animate-scroll-indicator absolute bottom-8 text-hero-text-muted">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M7 10l5 5 5-5" />
          </svg>
        </div>
      </section>

      {/* ====== ABOUT SECTION ====== */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 pb-24 pt-16 sm:px-6 lg:px-8">
        <h2 className="mb-4 text-center font-display text-3xl text-hero-text md:text-4xl">
          Smarter farming starts here
        </h2>
        <p className="mx-auto mb-16 max-w-2xl text-center text-sm leading-relaxed text-hero-text-muted">
          GrowGrid combines agronomic intelligence with your farm&rsquo;s unique parameters to
          deliver actionable, data-driven crop plans — no guesswork, no generic advice.
        </p>

        <div className="grid gap-6 md:grid-cols-3">
          {/* Card 1 */}
          <div
            ref={card1Ref}
            className={`rounded-2xl border border-white/10 bg-white/[0.03] p-8 backdrop-blur-sm transition-opacity ${
              card1Visible ? 'animate-card-visible' : 'opacity-0'
            }`}
            style={{ animationDelay: '0ms' }}
          >
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-hero-lime/10 text-2xl">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a3e635" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22c4-4 8-7.5 8-12a8 8 0 0 0-16 0c0 4.5 4 8 8 12z" />
                <circle cx="12" cy="10" r="3" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-hero-text">
              What is GrowGrid
            </h3>
            <p className="text-sm leading-relaxed text-hero-text-muted">
              An AI advisory platform that analyzes your farm parameters and generates
              a complete, personalized farming strategy — crop selection, economics,
              field layout, and government schemes — in minutes.
            </p>
          </div>

          {/* Card 2 */}
          <div
            ref={card2Ref}
            className={`rounded-2xl border border-white/10 bg-white/[0.03] p-8 backdrop-blur-sm transition-opacity ${
              card2Visible ? 'animate-card-visible' : 'opacity-0'
            }`}
            style={{ animationDelay: '150ms' }}
          >
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-hero-gold/10 text-2xl">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#c8a97e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-hero-text">
              Why it&rsquo;s needed
            </h3>
            <p className="text-sm leading-relaxed text-hero-text-muted">
              Most farmers lack access to expert crop planning, soil analysis
              interpretation, and ROI forecasting. Decisions that shape entire seasons
              are made on instinct — GrowGrid changes that with data.
            </p>
          </div>

          {/* Card 3 */}
          <div
            ref={card3Ref}
            className={`rounded-2xl border border-white/10 bg-white/[0.03] p-8 backdrop-blur-sm transition-opacity ${
              card3Visible ? 'animate-card-visible' : 'opacity-0'
            }`}
            style={{ animationDelay: '300ms' }}
          >
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-hero-lime/10 text-2xl">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#a3e635" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18M9 3v18" />
              </svg>
            </div>
            <h3 className="mb-2 text-lg font-semibold text-hero-text">
              What it does
            </h3>
            <p className="text-sm leading-relaxed text-hero-text-muted">
              Enter your land details — soil type, water availability, climate zone,
              budget — and receive a smart crop recommendation with a full consulting
              report including economics, field layout, and eligible schemes.
            </p>
          </div>
        </div>
      </section>

      {/* Gradient bridge: dark → light */}
      <div className="h-32 bg-gradient-to-b from-hero-bg to-surface-50" />
    </div>
  )
}
