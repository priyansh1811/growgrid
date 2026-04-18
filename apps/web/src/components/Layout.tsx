import { ReactNode } from 'react'

interface LayoutProps {
  children: ReactNode
  variant?: 'default' | 'planner'
}

export function Layout({ children, variant = 'default' }: LayoutProps) {
  const isPlanner = variant === 'planner'

  return (
    <div
      className={`min-h-screen ${
        isPlanner
          ? 'bg-[#0D2B1A]'
          : ''
      }`}
    >
      {/* Grain texture for planner */}
      {isPlanner && <div className="grain pointer-events-none fixed inset-0 z-0" />}

      <header
        className={`relative z-10 ${
          isPlanner
            ? 'border-b border-white/[0.06] bg-transparent'
            : 'border-b border-surface-200 bg-white shadow-sm'
        }`}
      >
        <div className="mx-auto flex h-14 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
          <span
            className={`flex items-center gap-2 text-lg font-semibold ${
              isPlanner ? 'text-accent-gold' : 'text-primary-800'
            }`}
          >
            <span className="text-2xl">🌾</span>
            GrowGrid
          </span>
          <span
            className={`ml-2 text-sm font-medium ${
              isPlanner ? 'text-white/25' : 'text-surface-500'
            }`}
          >
            Smart Farming Planner
          </span>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}
