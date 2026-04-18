import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FallingPattern } from '../ui/falling-pattern'

const STAGES = [
  { label: 'Validating farm profile', icon: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z', duration: 2000 },
  { label: 'Analyzing constraints', icon: 'M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75', duration: 3000 },
  { label: 'Scoring farming practices', icon: 'M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5', duration: 5000 },
  { label: 'Evaluating crop suitability', icon: 'M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z', duration: 5000 },
  { label: 'Building crop portfolio', icon: 'M2.25 7.125C2.25 6.504 2.754 6 3.375 6h6c.621 0 1.125.504 1.125 1.125v3.75c0 .621-.504 1.125-1.125 1.125h-6a1.125 1.125 0 01-1.125-1.125v-3.75zM14.25 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v5.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125v-5.25zM3.75 16.125c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125v2.25c0 .621-.504 1.125-1.125 1.125h-5.25a1.125 1.125 0 01-1.125-1.125v-2.25z', duration: 4000 },
  { label: 'Running financial analysis', icon: 'M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 00-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 01-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 003 15h-.75M15 10.5a3 3 0 11-6 0 3 3 0 016 0zm3 0h.008v.008H18V10.5zm-12 0h.008v.008H6V10.5z', duration: 5000 },
  { label: 'Matching government schemes', icon: 'M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z', duration: 4000 },
  { label: 'Generating grow guides', icon: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25', duration: 4000 },
  { label: 'Expert review & verification', icon: 'M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5', duration: 5000 },
  { label: 'Compiling your report', icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z', duration: 6000 },
]

const ENCOURAGEMENTS = [
  'Analyzing soil compatibility across your region...',
  'Cross-referencing historical market prices...',
  'Calculating optimal crop diversity ratios...',
  'Evaluating seasonal water requirements...',
  'Matching against 50+ farming practices...',
  'Simulating financial projections...',
  'Checking government subsidy eligibility...',
  'Preparing detailed grow calendars...',
]

export function PipelineLoader() {
  const [activeStage, setActiveStage] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [encourageIdx, setEncourageIdx] = useState(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Advance stages on a timer
  useEffect(() => {
    if (activeStage >= STAGES.length) return
    const dur = STAGES[activeStage].duration
    timerRef.current = setTimeout(() => {
      setActiveStage((s) => s + 1)
    }, dur)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [activeStage])

  // Elapsed timer
  useEffect(() => {
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(interval)
  }, [])

  // Rotate encouragement messages
  useEffect(() => {
    const interval = setInterval(
      () => setEncourageIdx((i) => (i + 1) % ENCOURAGEMENTS.length),
      4000
    )
    return () => clearInterval(interval)
  }, [])

  const formatTime = (s: number) =>
    `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-forest backdrop-blur-xl"
    >
      {/* Falling pattern background */}
      <div className="absolute inset-0 opacity-40">
        <FallingPattern
          color="#4A8C62"
          backgroundColor="#0D2B1A"
          duration={120}
          blurIntensity="0.8em"
          density={1}
          className="h-full [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_80%)]"
        />
      </div>

      {/* Grain overlay */}
      <div className="grain pointer-events-none absolute inset-0" />

      {/* Ambient glow */}
      <div className="absolute left-1/2 top-1/3 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent-gold/[0.04] blur-[120px]" />

      <div className="relative z-10 w-full max-w-md px-6">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="mb-10 text-center"
        >
          <h2 className="font-display text-2xl text-white sm:text-3xl">
            Building your plan
          </h2>
          <p className="mt-2 text-sm text-white/35">
            Our AI agents are analyzing your farm profile
          </p>
        </motion.div>

        {/* Pipeline stages */}
        <div className="space-y-0">
          {STAGES.map((stage, i) => {
            const completed = i < activeStage
            const active = i === activeStage

            return (
              <motion.div
                key={stage.label}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 + i * 0.06, duration: 0.4 }}
                className="flex items-start gap-4"
              >
                {/* Vertical connector + dot */}
                <div className="flex flex-col items-center">
                  <div className="relative">
                    {/* Pulse ring for active */}
                    {active && (
                      <motion.div
                        className="absolute inset-0 rounded-full bg-accent-gold/30"
                        animate={{ scale: [1, 2], opacity: [0.4, 0] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
                      />
                    )}
                    <div
                      className={`relative z-10 flex h-7 w-7 items-center justify-center rounded-full transition-all duration-500 ${
                        completed
                          ? 'bg-primary-500'
                          : active
                            ? 'pipeline-glow bg-accent-gold'
                            : 'bg-white/[0.06]'
                      }`}
                    >
                      <AnimatePresence mode="wait">
                        {completed ? (
                          <motion.svg
                            key="check"
                            initial={{ scale: 0, rotate: -90 }}
                            animate={{ scale: 1, rotate: 0 }}
                            exit={{ scale: 0 }}
                            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="white"
                            strokeWidth="3"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M20 6L9 17l-5-5" />
                          </motion.svg>
                        ) : active ? (
                          <motion.svg
                            key="icon"
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            width="13"
                            height="13"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#0D2B1A"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d={stage.icon} />
                          </motion.svg>
                        ) : (
                          <div className="h-1.5 w-1.5 rounded-full bg-white/15" />
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  {/* Connector line */}
                  {i < STAGES.length - 1 && (
                    <div className="relative h-5 w-[2px] overflow-hidden bg-white/[0.05]">
                      <motion.div
                        className="absolute inset-x-0 top-0 bg-primary-500"
                        initial={{ height: '0%' }}
                        animate={{ height: completed ? '100%' : '0%' }}
                        transition={{ duration: 0.4, ease: 'easeOut' }}
                      />
                    </div>
                  )}
                </div>

                {/* Label */}
                <div className="pb-5 pt-0.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-sm font-medium transition-colors duration-500 ${
                        completed
                          ? 'text-primary-400/60'
                          : active
                            ? 'text-accent-gold'
                            : 'text-white/20'
                      }`}
                    >
                      {stage.label}
                    </span>

                    {/* Bouncing dots for active */}
                    {active && (
                      <div className="pipeline-dot-bounce flex gap-0.5">
                        <span className="inline-block h-1 w-1 rounded-full bg-accent-gold" />
                        <span className="inline-block h-1 w-1 rounded-full bg-accent-gold" />
                        <span className="inline-block h-1 w-1 rounded-full bg-accent-gold" />
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Footer: elapsed + encouragement */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-8 text-center"
        >
          <AnimatePresence mode="wait">
            <motion.p
              key={encourageIdx}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="text-xs italic text-white/25"
            >
              {ENCOURAGEMENTS[encourageIdx]}
            </motion.p>
          </AnimatePresence>
          <p className="mt-3 text-xs tabular-nums text-white/15">
            {formatTime(elapsed)} elapsed
          </p>
        </motion.div>
      </div>
    </motion.div>
  )
}
