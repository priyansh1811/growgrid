import { useScroll, useTransform, useSpring, type MotionValue } from 'framer-motion'
import { useState, useEffect } from 'react'

interface HeroParallaxOptions {
  /** Vertical parallax factor. Positive = moves down on scroll. */
  speedY?: number
  /** Horizontal parallax factor. Positive = moves right on scroll. */
  speedX?: number
  /** Breakpoint below which parallax is disabled. Default 768. */
  disableBelow?: number
  /** Enable spring-based smoothing for buttery motion. */
  smooth?: boolean
  /** Spring stiffness (default 40). Lower = more lag/smoothness. */
  stiffness?: number
  /** Spring damping (default 20). Higher = less oscillation. */
  damping?: number
}

export function useHeroParallax(
  containerRef: React.RefObject<HTMLElement>,
  options: HeroParallaxOptions = {}
): { y: MotionValue<number>; x: MotionValue<number>; scrollYProgress: MotionValue<number> } {
  const { speedY = 0, speedX = 0, disableBelow = 768, smooth = false, stiffness = 40, damping = 20 } = options

  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < disableBelow)
    check()
    window.addEventListener('resize', check, { passive: true })
    return () => window.removeEventListener('resize', check)
  }, [disableBelow])

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  })

  const rawY = useTransform(
    scrollYProgress,
    [0, 1],
    isMobile ? [0, 0] : [0, speedY * 300]
  )

  const rawX = useTransform(
    scrollYProgress,
    [0, 1],
    isMobile ? [0, 0] : [0, speedX * 300]
  )

  const springConfig = { stiffness, damping, mass: 0.5 }
  const smoothY = useSpring(rawY, springConfig)
  const smoothX = useSpring(rawX, springConfig)

  const y = smooth ? smoothY : rawY
  const x = smooth ? smoothX : rawX

  return { y, x, scrollYProgress }
}
