import type {
  ClarificationResult,
  FormInputs,
  PlanResponse,
  RefinementResult,
} from '../types'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 300_000): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      signal: controller.signal,
      ...options,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error((err as { detail?: string }).detail || res.statusText)
    }
    return res.json() as Promise<T>
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error('Request timed out — the pipeline took too long. Please try again.')
    }
    throw e
  } finally {
    clearTimeout(timeoutId)
  }
}

// Re-export types so consumers can use either client or types
export type { ClarificationResult, FormInputs, PlanResponse, RefinementResult }

export const api = {
  health: () => request<{ status: string }>('/health'),

  clarify: (form: FormInputs) =>
    request<ClarificationResult>('/clarify', { method: 'POST', body: JSON.stringify(form) }),

  refine: (form: FormInputs, answers: { question_id: string; answer: string }[]) =>
    request<RefinementResult>('/refine', {
      method: 'POST',
      body: JSON.stringify({ form_inputs: form, answers }),
    }),

  planFromForm: (form: FormInputs, refinement: RefinementResult | null = null) =>
    request<PlanResponse>('/plan-from-form', {
      method: 'POST',
      body: JSON.stringify({ form_inputs: form, refinement }),
    }),
}
