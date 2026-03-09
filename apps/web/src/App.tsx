import { useState } from 'react'
import { api, type FormInputs, type ClarificationResult, type RefinementResult, type PlanResponse } from './api/client'
import { Layout } from './components/Layout'
import { FarmForm } from './components/FarmForm'
import { Clarification } from './components/Clarification'
import { PlanResults } from './components/PlanResults'

type Step = 'form' | 'clarify' | 'results'

export default function App() {
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
      } else {
        await runPipeline(null)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Clarification check failed')
    } finally {
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
    <Layout>
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          {error}
        </div>
      )}

      {step === 'form' && (
        <FarmForm
          form={form}
          onChange={setForm}
          onGenerate={handleGenerate}
          loading={loading}
        />
      )}

      {step === 'clarify' && clarification && (
        <Clarification
          clarification={clarification}
          onSubmit={handleClarificationSubmit}
          onSkip={handleClarificationSkip}
          loading={loading}
        />
      )}

      {step === 'results' && plan && (
        <PlanResults plan={plan} onBack={handleBack} />
      )}
    </Layout>
  )
}
