import { motion } from 'framer-motion'

interface StepIndicatorProps {
  steps: string[]
  current: number
}

export function StepIndicator({ steps, current }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center gap-0">
      {steps.map((label, i) => {
        const completed = i < current
        const active = i === current

        return (
          <div key={label} className="flex items-center">
            {/* Node */}
            <div className="flex flex-col items-center">
              <div className="relative">
                {/* Pulse ring for active */}
                {active && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-accent-gold"
                    animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
                  />
                )}

                <motion.div
                  className={`relative z-10 flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold transition-colors duration-300 ${
                    completed
                      ? 'bg-primary-500 text-white'
                      : active
                        ? 'border-2 border-accent-gold bg-accent-gold/15 text-accent-gold'
                        : 'border border-white/15 bg-white/[0.04] text-white/30'
                  }`}
                  animate={active ? { scale: [1, 1.05, 1] } : {}}
                  transition={active ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : {}}
                >
                  {completed ? (
                    <motion.svg
                      initial={{ scale: 0, rotate: -90 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M20 6L9 17l-5-5" />
                    </motion.svg>
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </motion.div>
              </div>

              {/* Label */}
              <span
                className={`mt-2 max-w-[80px] text-center text-[10px] font-medium leading-tight tracking-wide ${
                  completed
                    ? 'text-primary-400'
                    : active
                      ? 'text-accent-gold'
                      : 'text-white/25'
                }`}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className="mx-2 mb-5 h-[2px] w-10 overflow-hidden rounded-full bg-white/[0.06] sm:mx-3 sm:w-16">
                <motion.div
                  className="h-full rounded-full bg-primary-500"
                  initial={{ width: '0%' }}
                  animate={{ width: completed ? '100%' : '0%' }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
