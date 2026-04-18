import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { FormInputs } from '../../api/client'
import { StepIndicator } from './StepIndicator'
import { RadioCardGroup } from './RadioCardGroup'
import {
  CATEGORY_OPTS,
  WATER_OPTS,
  IRRIGATION_OPTS,
  LABOUR_OPTS,
  GOAL_OPTS,
  RISK_OPTS,
  MONTH_OPTS,
} from '../FarmForm'

interface FormWizardProps {
  form: FormInputs
  onChange: (f: FormInputs) => void
  onGenerate: () => void
  loading: boolean
}

const STEP_LABELS = ['About You', 'Your Land', 'Goals', 'Timeline']

const slideVariants = {
  enter: (dir: number) => ({
    x: dir > 0 ? 280 : -280,
    opacity: 0,
    scale: 0.96,
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
  },
  exit: (dir: number) => ({
    x: dir > 0 ? -280 : 280,
    opacity: 0,
    scale: 0.96,
  }),
}

const fieldVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.08 * i, duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
  }),
}

function FieldGroup({
  label,
  tooltip,
  children,
  error,
  index = 0,
}: {
  label: string
  tooltip?: string
  children: React.ReactNode
  error?: string
  index?: number
}) {
  return (
    <motion.div custom={index} variants={fieldVariants} initial="hidden" animate="visible">
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-white/40">
        {label}
        {tooltip && (
          <span className="group relative">
            <span className="inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full bg-white/[0.06] text-[9px] font-bold text-white/30">
              ?
            </span>
            <span className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-white/10 bg-forest px-3 py-2 text-xs font-normal normal-case tracking-normal text-white/70 opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
              {tooltip}
            </span>
          </span>
        )}
      </label>
      {children}
      {error && (
        <p className="mt-1.5 text-xs font-medium text-red-400">{error}</p>
      )}
    </motion.div>
  )
}

export function FormWizard({ form, onChange, onGenerate, loading }: FormWizardProps) {
  const [wizardStep, setWizardStep] = useState(0)
  const [direction, setDirection] = useState(1)

  const update = (k: keyof FormInputs, v: string | number | null) =>
    onChange({ ...form, [k]: v })

  // Per-step validation
  const stepErrors: Record<number, Partial<Record<keyof FormInputs, string>>> = {
    0: {},
    1: {
      ...(form.location.trim() === '' ? { location: 'Location is required' } : {}),
      ...(form.land_area_acres <= 0 ? { land_area_acres: 'Must be > 0' } : {}),
    },
    2: {
      ...(form.budget_total_inr <= 0 ? { budget_total_inr: 'Must be > 0' } : {}),
    },
    3: {
      ...(form.time_horizon_years <= 0 ? { time_horizon_years: 'Must be > 0' } : {}),
    },
  }

  const currentErrors = stepErrors[wizardStep] || {}
  const hasErrors = Object.keys(currentErrors).length > 0

  const goNext = () => {
    if (wizardStep < 3) {
      setDirection(1)
      setWizardStep((s) => s + 1)
    }
  }
  const goBack = () => {
    if (wizardStep > 0) {
      setDirection(-1)
      setWizardStep((s) => s - 1)
    }
  }

  const stepTitles = [
    "Let's get to know you",
    'Tell us about your farm',
    'Your vision & resources',
    'When do we begin?',
  ]
  const stepSubtitles = [
    'Basic details to personalize your plan',
    'Physical characteristics of your land',
    'Budget, labour, and farming goals',
    'Set your planning timeline',
  ]

  return (
    <div className="mx-auto max-w-2xl">
      {/* Step indicator */}
      <div className="mb-10">
        <StepIndicator steps={STEP_LABELS} current={wizardStep} />
      </div>

      {/* Wizard card */}
      <div className="form-card-glass grain relative overflow-hidden rounded-2xl p-8 sm:p-10">
        {/* Step title */}
        <AnimatePresence mode="wait">
          <motion.div
            key={`title-${wizardStep}`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3 }}
            className="mb-8"
          >
            <h2 className="font-display text-2xl font-normal text-white sm:text-3xl">
              {stepTitles[wizardStep]}
            </h2>
            <p className="mt-1.5 text-sm text-white/35">{stepSubtitles[wizardStep]}</p>
          </motion.div>
        </AnimatePresence>

        {/* Step content */}
        <div className="relative min-h-[280px]">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={wizardStep}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            >
              {wizardStep === 0 && <StepAboutYou form={form} update={update} />}
              {wizardStep === 1 && (
                <StepYourLand form={form} update={update} errors={currentErrors} />
              )}
              {wizardStep === 2 && (
                <StepGoals form={form} update={update} errors={currentErrors} />
              )}
              {wizardStep === 3 && (
                <StepTimeline form={form} update={update} errors={currentErrors} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <div className="mt-10 flex items-center justify-between">
          <div>
            {wizardStep > 0 && (
              <motion.button
                type="button"
                onClick={goBack}
                whileHover={{ x: -3 }}
                whileTap={{ scale: 0.96 }}
                className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white/50 transition-colors hover:bg-white/[0.04] hover:text-white/70"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 19l-7-7 7-7" />
                </svg>
                Back
              </motion.button>
            )}
          </div>

          <div className="flex items-center gap-3">
            {hasErrors && (
              <p className="text-xs text-red-400/80">Fix errors to continue</p>
            )}

            {wizardStep < 3 ? (
              <motion.button
                type="button"
                onClick={goNext}
                disabled={hasErrors}
                whileHover={hasErrors ? {} : { x: 3, scale: 1.02 }}
                whileTap={hasErrors ? {} : { scale: 0.97 }}
                className="flex items-center gap-2 rounded-xl bg-white/[0.08] px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition-all hover:bg-white/[0.12] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </motion.button>
            ) : (
              <motion.button
                type="button"
                onClick={onGenerate}
                disabled={loading || hasErrors}
                whileHover={loading || hasErrors ? {} : { scale: 1.03 }}
                whileTap={loading || hasErrors ? {} : { scale: 0.97 }}
                className="relative overflow-hidden rounded-xl bg-gradient-to-r from-accent-gold-dark via-accent-gold to-accent-gold-light px-8 py-3 text-sm font-bold text-forest shadow-lg shadow-accent-gold/20 transition-all hover:shadow-accent-gold/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <span className="relative z-10 flex items-center gap-2">
                  Generate My Plan
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                  </svg>
                </span>
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────── Step Components ────────────────────────── */

function StepAboutYou({
  form,
  update,
}: {
  form: FormInputs
  update: (k: keyof FormInputs, v: string | number | null) => void
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <FieldGroup label="Full Name" index={0}>
          <input
            type="text"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            className="form-input-dark"
            placeholder="Your name"
          />
        </FieldGroup>
        <FieldGroup label="Email Address" index={1}>
          <input
            type="email"
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
            className="form-input-dark"
            placeholder="you@example.com"
          />
        </FieldGroup>
      </div>

      <FieldGroup label="Category" tooltip="Social category for government scheme eligibility" index={2}>
        <RadioCardGroup
          groupId="category"
          options={CATEGORY_OPTS.map((o) => ({ value: o.value, label: o.label }))}
          value={form.category}
          onChange={(v) => update('category', v)}
          columns={4}
        />
      </FieldGroup>
    </div>
  )
}

function StepYourLand({
  form,
  update,
  errors,
}: {
  form: FormInputs
  update: (k: keyof FormInputs, v: string | number | null) => void
  errors: Partial<Record<keyof FormInputs, string>>
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <FieldGroup
          label="Location (State, District)"
          tooltip="Used for climate matching, scheme eligibility, and crop suitability"
          error={errors.location}
          index={0}
        >
          <input
            type="text"
            value={form.location}
            onChange={(e) => update('location', e.target.value)}
            className={`form-input-dark ${errors.location ? '!border-red-400/50 !focus:border-red-400' : ''}`}
            placeholder="e.g. Karnataka, Bangalore Rural"
          />
        </FieldGroup>

        <FieldGroup
          label="Land Area (acres)"
          tooltip="Total cultivable land. Affects crop diversity."
          error={errors.land_area_acres}
          index={1}
        >
          <input
            type="number"
            min={0.1}
            max={1000}
            step={0.5}
            value={form.land_area_acres}
            onChange={(e) => update('land_area_acres', parseFloat(e.target.value) || 0)}
            className={`form-input-dark ${errors.land_area_acres ? '!border-red-400/50' : ''}`}
          />
        </FieldGroup>
      </div>

      <FieldGroup label="Water Availability" tooltip="Overall water access level" index={2}>
        <RadioCardGroup
          groupId="water"
          options={WATER_OPTS}
          value={form.water_availability}
          onChange={(v) => update('water_availability', v)}
          columns={3}
        />
      </FieldGroup>

      <FieldGroup label="Irrigation Source" tooltip="Primary irrigation method" index={3}>
        <RadioCardGroup
          groupId="irrigation"
          options={IRRIGATION_OPTS.map((o) => ({ value: o.value, label: o.label }))}
          value={form.irrigation_source}
          onChange={(v) => update('irrigation_source', v)}
          columns={3}
        />
      </FieldGroup>
    </div>
  )
}

function StepGoals({
  form,
  update,
  errors,
}: {
  form: FormInputs
  update: (k: keyof FormInputs, v: string | number | null) => void
  errors: Partial<Record<keyof FormInputs, string>>
}) {
  return (
    <div className="space-y-6">
      <FieldGroup
        label="Total Budget (INR)"
        tooltip="Entire farming budget including CAPEX and OPEX"
        error={errors.budget_total_inr}
        index={0}
      >
        <input
          type="number"
          min={1000}
          max={100_000_000}
          step={10000}
          value={form.budget_total_inr}
          onChange={(e) => update('budget_total_inr', parseInt(e.target.value, 10) || 0)}
          className={`form-input-dark ${errors.budget_total_inr ? '!border-red-400/50' : ''}`}
        />
        {form.land_area_acres > 0 && form.budget_total_inr > 0 && (
          <p className="mt-1.5 text-xs text-accent-gold/50">
            {`\u20B9${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(form.budget_total_inr / form.land_area_acres)}/acre`}
          </p>
        )}
      </FieldGroup>

      <FieldGroup label="Labour Availability" tooltip="Affects which practices are recommended" index={1}>
        <RadioCardGroup
          groupId="labour"
          options={LABOUR_OPTS}
          value={form.labour_availability}
          onChange={(v) => update('labour_availability', v)}
          columns={3}
        />
      </FieldGroup>

      <FieldGroup label="Primary Goal" tooltip="Drives weight distribution across scoring dimensions" index={2}>
        <RadioCardGroup
          groupId="goal"
          options={GOAL_OPTS}
          value={form.goal}
          onChange={(v) => update('goal', v)}
          columns={2}
        />
      </FieldGroup>

      <FieldGroup label="Risk Tolerance" tooltip="Low = safe proven crops. High = experimental/high-reward." index={3}>
        <RadioCardGroup
          groupId="risk"
          options={RISK_OPTS}
          value={form.risk_tolerance}
          onChange={(v) => update('risk_tolerance', v)}
          columns={3}
        />
      </FieldGroup>
    </div>
  )
}

function StepTimeline({
  form,
  update,
  errors,
}: {
  form: FormInputs
  update: (k: keyof FormInputs, v: string | number | null) => void
  errors: Partial<Record<keyof FormInputs, string>>
}) {
  return (
    <div className="space-y-6">
      <FieldGroup
        label="Time Horizon (years)"
        tooltip="Planning period. Short horizons exclude long-gestation crops."
        error={errors.time_horizon_years}
        index={0}
      >
        <input
          type="number"
          min={0.5}
          max={30}
          step={0.5}
          value={form.time_horizon_years}
          onChange={(e) => update('time_horizon_years', parseFloat(e.target.value) || 0)}
          className={`form-input-dark ${errors.time_horizon_years ? '!border-red-400/50' : ''}`}
        />
      </FieldGroup>

      <FieldGroup label="Planning Month" tooltip="Month when you plan to start farming" index={1}>
        <RadioCardGroup
          groupId="month"
          options={MONTH_OPTS.map((o) => ({
            value: String(o.value),
            label: o.label,
          }))}
          value={String(form.planning_month ?? 0)}
          onChange={(v) => {
            const num = parseInt(v, 10)
            update('planning_month', num === 0 ? null : num)
          }}
          columns={4}
        />
      </FieldGroup>

      {/* Summary preview */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="mt-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-5"
      >
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/30">
          Plan Summary
        </p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            ['Location', form.location || '—'],
            ['Land', `${form.land_area_acres} acres`],
            ['Budget', `\u20B9${new Intl.NumberFormat('en-IN').format(form.budget_total_inr)}`],
            ['Goal', GOAL_OPTS.find((o) => o.value === form.goal)?.label || form.goal],
            ['Horizon', `${form.time_horizon_years} yrs`],
            ['Risk', RISK_OPTS.find((o) => o.value === form.risk_tolerance)?.label || form.risk_tolerance],
          ].map(([k, v]) => (
            <div key={k} className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2">
              <span className="text-white/30">{k}</span>
              <span className="font-medium text-accent-gold/80">{v}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}
