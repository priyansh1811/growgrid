import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Navbar } from './Navbar'
import { HeroSection } from './HeroSection'
import { ProblemSection } from './ProblemSection'
import { HowItWorksSection } from './HowItWorksSection'
import { AgentPipelineSection } from './AgentPipelineSection'
import { ExplainabilitySection } from './ExplainabilitySection'
import { ReportPreviewSection } from './ReportPreviewSection'
import { ForWhomSection } from './ForWhomSection'
import { CTASection } from './CTASection'
import { Footer } from './Footer'

export function MarketingPage() {
  const [showBackToTop, setShowBackToTop] = useState(false)

  useEffect(() => {
    const onScroll = () => setShowBackToTop(window.scrollY > 300)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      <Navbar />
      <HeroSection />
      <ProblemSection />
      {/* white → cream */}
      <div className="h-20" style={{ background: 'linear-gradient(to bottom, #FFFFFF, #F5F2EC)' }} />
      <HowItWorksSection />
      {/* cream → dark neutral */}
      <div className="h-20" style={{ background: 'linear-gradient(to bottom, #F5F2EC, #0C0D10)' }} />
      <AgentPipelineSection />
      {/* dark neutral → cream */}
      <div className="h-20" style={{ background: 'linear-gradient(to bottom, #0C0D10, #F5F2EC)' }} />
      <ExplainabilitySection />
      <ReportPreviewSection />
      {/* cream → cream (ForWhom) — no bridge needed */}
      <ForWhomSection />
      <CTASection />
      <Footer />

      {/* Back to top */}
      <AnimatePresence>
        {showBackToTop && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="fixed bottom-6 right-6 z-50 flex h-10 w-10 items-center justify-center rounded-full bg-forest/90 text-white shadow-lg backdrop-blur transition-colors hover:bg-forest"
            aria-label="Back to top"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 15l-6-6-6 6" />
            </svg>
          </motion.button>
        )}
      </AnimatePresence>
    </>
  )
}
