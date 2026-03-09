import { ReactNode } from 'react'

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-surface-200 bg-white shadow-sm">
        <div className="mx-auto flex h-14 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
          <span className="flex items-center gap-2 text-lg font-semibold text-primary-800">
            <span className="text-2xl">🌾</span>
            GrowGrid
          </span>
          <span className="ml-2 text-sm font-medium text-surface-500">
            Smart Farming Planner
          </span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
    </div>
  )
}
