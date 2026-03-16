import { useEffect, useRef, useState } from 'react'

export function useIntersectionFade(
  options?: IntersectionObserverInit
): [React.RefObject<HTMLDivElement>, boolean] {
  const ref = useRef<HTMLDivElement>(null!)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setIsVisible(true)
        observer.unobserve(el)
      }
    }, { threshold: 0.15, ...options })

    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return [ref, isVisible]
}
