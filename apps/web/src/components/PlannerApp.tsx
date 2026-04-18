import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api, type FormInputs, type ClarificationResult, type RefinementResult, type PlanResponse } from '../api/client'
import { Layout } from './Layout'
import { FarmForm } from './FarmForm'
import { Clarification } from './Clarification'
import { PlanResults } from './PlanResults'
import { PipelineLoader } from './form/PipelineLoader'

type Step = 'form' | 'clarify' | 'results'

const pageVariants = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -24 },
}

export function PlannerApp() {
  const [form, setForm] = useState<FormInputs>({
    name: '',
    email: '',
    category: 'general',
    location: 'Maharashtra, Pune',
    land_area_acres: 5,
    water_availability: 'MED',
    irrigation_source: 'BOREWELL',
    budget_total_inr: 300_000,
    labour_availability: 'MED',
    goal: 'MAXIMIZE_PROFIT',
    time_horizon_years: 2,
    risk_tolerance: 'MED',
  })
  const [step, setStep] = useState<Step>('form')
  const [clarification, setClarification] = useState<ClarificationResult | null>(null)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runPipeline = async (refinement: RefinementResult | null) => {
    setError(null)
    setLoading(true)
    try {
      const res = await api.planFromForm(form, refinement)
      setPlan(res)
      setStep('results')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pipeline failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    setError(null)
    setLoading(true)
    try {
      const result = await api.clarify(form)
      if (result.clarification_needed && result.questions.length > 0) {
        setClarification(result)
        setStep('clarify')
        setLoading(false)
      } else {
        await runPipeline(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Clarification check failed')
      setLoading(false)
    }
  }

  const handleClarificationSubmit = async (answers: { question_id: string; answer: string }[]) => {
    setError(null)
    setLoading(true)
    try {
      const refinement = await api.refine(form, answers)
      await runPipeline(refinement)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Refinement or pipeline failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClarificationSkip = () => runPipeline(null)

  const handleBack = () => {
    setStep('form')
    setClarification(null)
    setPlan(null)
    setError(null)
  }

  return (
    <>
      <Layout variant="planner">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto mb-6 max-w-2xl rounded-xl border border-red-500/20 bg-red-500/[0.08] px-5 py-3 text-sm text-red-300"
          >
            {error}
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {step === 'form' && (
            <motion.div
              key="form"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <FarmForm
                form={form}
                onChange={setForm}
                onGenerate={handleGenerate}
                loading={loading}
              />
            </motion.div>
          )}

          {step === 'clarify' && clarification && (
            <motion.div
              key="clarify"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <Clarification
                clarification={clarification}
                onSubmit={handleClarificationSubmit}
                onSkip={handleClarificationSkip}
                loading={loading}
              />
            </motion.div>
          )}

          {step === 'results' && plan && (
            <motion.div
              key="results"
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              <PlanResults plan={plan} onBack={handleBack} />
            </motion.div>
          )}
        </AnimatePresence>
      </Layout>

      {/* Pipeline loader overlay */}
      <AnimatePresence>
        {loading && <PipelineLoader />}
      </AnimatePresence>
    </>
  )
}
