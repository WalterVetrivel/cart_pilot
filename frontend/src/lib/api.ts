import { auth } from './firebase'

export interface ApiError {
  error: { code: string; message: string }
}

export class ApiRequestError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

/** Calls the backend under /api, attaching the Firebase ID token when signed in. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const user = auth?.currentUser
  if (user) headers.set('Authorization', `Bearer ${await user.getIdToken()}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiError | null
    throw new ApiRequestError(
      res.status,
      body?.error.code ?? 'http_error',
      body?.error.message ?? res.statusText,
    )
  }
  return (await res.json()) as T
}

export interface Health {
  status: string
  model: string
}

export const getHealth = () => api<Health>('/health')

export const formatINR = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value)

// --- Lists (SPEC §6.1, §8.1) -------------------------------------------------
export const UNITS = ['kg', 'g', 'l', 'ml', 'pcs', 'pack'] as const
export type Unit = (typeof UNITS)[number]

export interface ShoppingItem {
  id?: string
  canonical_name: string
  original_text: string
  quantity: number
  unit: Unit | null
  brand_preference: string | null
  category: string
  notes: string | null
  optional: boolean
}

export interface Candidate {
  product_id: string
  store_id: string
  name: string
  brand: string
  price: number
  qty: number
  line_price: number
  rating: number
  in_stock: boolean
}

export interface ListResponse {
  list_id: string
  source_type: 'text' | 'image' | 'audio' | 'pdf' | 'docx'
  detected_language: string
  items: ShoppingItem[]
  matches: Record<string, Candidate[]>
}

export function parseList(input: { text?: string; file?: Blob; filename?: string }): Promise<ListResponse> {
  const form = new FormData()
  if (input.text) form.append('text', input.text)
  if (input.file) form.append('file', input.file, input.filename ?? 'upload')
  return api<ListResponse>('/parse', { method: 'POST', body: form })
}

export const getList = (listId: string) => api<ListResponse>(`/lists/${listId}`)

export const updateList = (listId: string, items: ShoppingItem[], detectedLanguage: string) =>
  api<ListResponse>(`/lists/${listId}`, {
    method: 'PUT',
    body: JSON.stringify({ items, detected_language: detectedLanguage }),
  })
