import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

function LeafIcon({ className = '' }: { className?: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const links = [
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'The Agents', href: '#agents' },
    { label: 'Research', href: '#report' },
  ]

  const scrollTo = (href: string) => {
    setMenuOpen(false)
    const el = document.querySelector(href)
    el?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <motion.nav
      className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-300 ${
        scrolled ? 'bg-[#0a0d0a]/95 backdrop-blur-md shadow-lg' : 'bg-transparent'
      }`}
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <a
          href="#"
          onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          className="flex items-center gap-1.5 text-lg font-bold text-white"
        >
          <LeafIcon className="text-accent-gold" />
          <span>GrowGrid<span className="text-text-muted-dark">.ai</span></span>
        </a>

        {/* Desktop nav */}
        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <button
              key={l.href}
              onClick={() => scrollTo(l.href)}
              className="text-sm font-medium text-white/50 transition-colors hover:text-white/80"
            >
              {l.label}
            </button>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden items-center gap-4 md:flex">
          <button className="text-sm font-medium text-white/50 transition-colors hover:text-white/80">
            Sign In
          </button>
          <button
            onClick={() => navigate('/plan')}
            className="rounded-full bg-accent-gold px-6 py-2 text-sm font-semibold text-forest transition-all duration-300 hover:bg-accent-gold-light"
          >
            Get Free Plan
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="flex flex-col gap-1.5 md:hidden"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <motion.span
            animate={menuOpen ? { rotate: 45, y: 6 } : { rotate: 0, y: 0 }}
            className="block h-0.5 w-6 bg-white"
          />
          <motion.span
            animate={menuOpen ? { opacity: 0 } : { opacity: 1 }}
            className="block h-0.5 w-6 bg-white"
          />
          <motion.span
            animate={menuOpen ? { rotate: -45, y: -6 } : { rotate: 0, y: 0 }}
            className="block h-0.5 w-6 bg-white"
          />
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden bg-[#0a0d0a]/95 backdrop-blur-md md:hidden"
          >
            <div className="flex flex-col gap-2 px-4 pb-6 pt-2">
              {links.map((l) => (
                <button
                  key={l.href}
                  onClick={() => scrollTo(l.href)}
                  className="py-2 text-left text-sm font-medium text-white/60 hover:text-white/90"
                >
                  {l.label}
                </button>
              ))}
              <hr className="border-white/10" />
              <button
                onClick={() => { setMenuOpen(false); navigate('/plan') }}
                className="mt-2 rounded-full bg-accent-gold px-6 py-3 text-center text-sm font-semibold text-forest"
              >
                Get Free Plan
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}
