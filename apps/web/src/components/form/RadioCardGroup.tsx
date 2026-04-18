import { motion } from 'framer-motion'
import type { ReactNode } from 'react'

interface Option<T extends string> {
  value: T
  label: string
  hint?: string
  icon?: ReactNode
}

interface RadioCardGroupProps<T extends string> {
  options: Option<T>[]
  value: T
  onChange: (v: T) => void
  columns?: 2 | 3 | 4
  groupId: string
}

export function RadioCardGroup<T extends string>({
  options,
  value,
  onChange,
  columns = 3,
  groupId,
}: RadioCardGroupProps<T>) {
  const colClass =
    columns === 2
      ? 'grid-cols-1 sm:grid-cols-2'
      : columns === 4
        ? 'grid-cols-2 sm:grid-cols-4'
        : 'grid-cols-1 sm:grid-cols-3'

  return (
    <div className={`grid gap-3 ${colClass}`}>
      {options.map((opt) => {
        const selected = opt.value === value
        return (
          <motion.button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            whileHover={{ y: -2, scale: 1.015 }}
            whileTap={{ scale: 0.97 }}
            className={`relative overflow-hidden rounded-xl border px-4 py-3.5 text-left transition-colors duration-200 ${
              selected
                ? 'border-accent-gold/60 bg-accent-gold/[0.08]'
                : 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.16] hover:bg-white/[0.05]'
            }`}
          >
            {/* Animated selection highlight */}
            {selected && (
              <motion.div
                layoutId={`radio-highlight-${groupId}`}
                className="absolute inset-0 rounded-xl border border-accent-gold/40 bg-accent-gold/[0.06]"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}

            <div className="relative z-10 flex items-start gap-3">
              {/* Radio indicator */}
              <div
                className={`mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-200 ${
                  selected
                    ? 'border-accent-gold bg-accent-gold'
                    : 'border-white/20 bg-transparent'
                }`}
              >
                {selected && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 25 }}
                    className="h-[6px] w-[6px] rounded-full bg-forest"
                  />
                )}
              </div>

              <div className="min-w-0">
                {opt.icon && <div className="mb-1">{opt.icon}</div>}
                <p
                  className={`text-sm font-medium leading-tight ${
                    selected ? 'text-accent-gold-light' : 'text-white/80'
                  }`}
                >
                  {opt.label}
                </p>
                {opt.hint && (
                  <p
                    className={`mt-0.5 text-xs leading-snug ${
                      selected ? 'text-accent-gold/60' : 'text-white/30'
                    }`}
                  >
                    {opt.hint}
                  </p>
                )}
              </div>
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
