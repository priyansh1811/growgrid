import { useState } from 'react'
import type { ClarificationResult } from '../api/client'

interface ClarificationProps {
  clarification: ClarificationResult
  onSubmit: (answers: { question_id: string; answer: string }[]) => void
  onSkip: () => void
  loading: boolean
}

export function Clarification({ clarification, onSubmit, onSkip, loading }: ClarificationProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const handleSubmit = () => {
    const list = clarification.questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] ?? '',
    }))
    onSubmit(list)
  }

  return (
    <div className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm">
      <h2 className="mb-2 text-xl font-semibold text-slate-800">
        A few questions for better recommendations
      </h2>
      {clarification.message && (
        <p className="mb-6 rounded-lg bg-primary-50 p-3 text-sm text-primary-800">
          {clarification.message}
        </p>
      )}
      <div className="space-y-6">
        {clarification.questions.map((q) => (
          <div key={q.id}>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              {q.question}
            </label>
            {q.suggested_options && q.suggested_options.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {q.suggested_options.map((opt) => (
                  <label key={opt} className="flex cursor-pointer items-center gap-2">
                    <input
                      type="radio"
                      name={q.id}
                      value={opt}
                      checked={answers[q.id] === opt}
                      onChange={() => setAnswers((a) => ({ ...a, [q.id]: opt }))}
                      className="h-4 w-4 border-surface-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm">{opt}</span>
                  </label>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={answers[q.id] ?? ''}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                placeholder="Your answer (optional)"
                className="w-full max-w-md rounded-lg border border-surface-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
            )}
          </div>
        ))}
      </div>
      <div className="mt-8 flex gap-3">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={loading}
          className="rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-60"
        >
          {loading ? 'Running…' : 'Submit answers and generate plan'}
        </button>
        <button
          type="button"
          onClick={onSkip}
          disabled={loading}
          className="rounded-lg border border-surface-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-surface-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-60"
        >
          Skip and use my form as-is
        </button>
      </div>
    </div>
  )
}
