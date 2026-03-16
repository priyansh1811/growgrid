import { useEffect, useState } from 'react'
import { useInView } from 'react-intersection-observer'

export function useCountUp(target: number, duration = 2) {
  const [count, setCount] = useState(0)
  const { ref, inView } = useInView({ threshold: 0.3, triggerOnce: true })

  useEffect(() => {
    if (!inView) return

    const start = performance.now()
    const step = (now: number) => {
      const elapsed = (now - start) / 1000
      const progress = Math.min(elapsed / duration, 1)
      // ease-out quad
      const eased = 1 - (1 - progress) * (1 - progress)
      setCount(Math.round(eased * target))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [inView, target, duration])

  return { ref, count }
}
