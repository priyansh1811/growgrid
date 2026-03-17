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
    { label: 'How It\'s Built', href: '#agents' },
    { label: 'Sample Report', href: '#report' },
  ]

  const scrollTo = (href: string) => {
    setMenuOpen(false)
    const el = document.querySelector(href)
    el?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <motion.nav
      className="fixed inset-x-0 top-0 z-50 px-4 pt-4 sm:px-6 lg:px-8"
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
    >
      <div
        className={`mx-auto flex max-w-7xl items-center justify-between rounded-full border px-4 py-3 transition-all duration-300 sm:px-5 ${
          scrolled
            ? 'border-white/12 bg-[#071018]/78 shadow-[0_20px_60px_rgba(0,0,0,0.28)] backdrop-blur-xl'
            : 'border-white/10 bg-white/[0.05] backdrop-blur-md'
        }`}
      >
        {/* Logo */}
        <a
          href="#"
          onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
          className="flex items-center gap-2.5 text-white"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.06]">
            <LeafIcon className="text-[#dcc8a8]" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-[0.08em] text-white">GrowGrid</span>
            <span className="mt-1 text-[10px] font-medium uppercase tracking-[0.28em] text-white/42">
              AI Farm Planning
            </span>
          </span>
        </a>

        {/* Desktop nav */}
        <div className="hidden items-center gap-2 rounded-full border border-white/8 bg-black/10 px-2 py-1 md:flex">
          {links.map((l) => (
            <button
              key={l.href}
              onClick={() => scrollTo(l.href)}
              className="rounded-full px-4 py-2 text-sm font-medium text-white/54 transition-colors hover:bg-white/[0.06] hover:text-white/86"
            >
              {l.label}
            </button>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden items-center gap-4 md:flex">
          <button className="text-sm font-medium text-white/54 transition-colors hover:text-white/84">
            Sign In
          </button>
          <button
            onClick={() => navigate('/plan')}
            className="rounded-full bg-[#e7dbc6] px-6 py-2.5 text-sm font-semibold text-[#10211a] transition-transform duration-300 hover:-translate-y-0.5"
            style={{
              boxShadow: '0 16px 40px rgba(231, 219, 198, 0.16), 0 4px 16px rgba(0, 0, 0, 0.18)',
            }}
          >
            Get Your Free Plan
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          className="flex flex-col gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 md:hidden"
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
            className="absolute inset-x-4 top-[calc(100%+0.75rem)] overflow-hidden rounded-[28px] border border-white/10 bg-[#071018]/88 shadow-[0_22px_60px_rgba(0,0,0,0.24)] backdrop-blur-xl md:hidden sm:inset-x-6 lg:inset-x-8"
          >
            <div className="flex flex-col gap-2 px-4 pb-5 pt-4">
              {links.map((l) => (
                <button
                  key={l.href}
                  onClick={() => scrollTo(l.href)}
                  className="rounded-2xl px-3 py-2.5 text-left text-sm font-medium text-white/66 transition-colors hover:bg-white/[0.05] hover:text-white"
                >
                  {l.label}
                </button>
              ))}
              <hr className="border-white/10" />
              <button
                onClick={() => { setMenuOpen(false); navigate('/plan') }}
                className="mt-2 rounded-full bg-[#e7dbc6] px-6 py-3 text-center text-sm font-semibold text-[#10211a]"
              >
                Get Your Free Plan
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  )
}
