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
  rating_count: number
  pack_size: number
  pack_unit: string
  in_stock: boolean
  brand_match: boolean
}

export interface ListResponse {
  list_id: string
  source_type: 'text' | 'image' | 'audio' | 'pdf' | 'docx'
  detected_language: string
  items: ShoppingItem[]
  matches: Record<string, Candidate[]>
}

export function parseList(input: {
  text?: string
  file?: Blob
  filename?: string
  /** Append to this list instead of starting a new one. */
  listId?: string
}): Promise<ListResponse> {
  const form = new FormData()
  if (input.listId) form.append('list_id', input.listId)
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

// --- Ranking and cart plans (SPEC §8.2, §8.3) --------------------------------
export interface Weights {
  price: number
  rating: number
  delivery: number
  availability: number
}

export type Preset = 'cheapest' | 'balanced' | 'fastest'

export const PRESETS: Record<Preset, Weights> = {
  cheapest: { price: 0.75, rating: 0.1, delivery: 0.05, availability: 0.1 },
  balanced: { price: 0.45, rating: 0.25, delivery: 0.2, availability: 0.1 },
  fastest: { price: 0.2, rating: 0.15, delivery: 0.55, availability: 0.1 },
}

export interface ScoredCandidate extends Candidate {
  score: number
  eta_minutes: number
  eta_label: string
}

export interface RankedItem {
  item_id: string
  candidates: ScoredCandidate[]
}

export interface StorePlan {
  store_id: string
  lines: { item_id: string; item_name: string; product_id: string; name: string; qty: number; line_price: number }[]
  subtotal: number
  delivery_fee: number
  voucher: { code: string | null; discount: number; voucher_id?: string | null } | null
  total: number
  eta: string
  eta_minutes: number
}

export interface CartPlan {
  plan_id: string
  label: 'best' | 'single_store' | 'fastest'
  stores: StorePlan[]
  grand_total: number
  effective_total: number
  savings_vs_single_store: number
  unavailable_items: string[]
  explanation: { headline: string; bullets: string[] }
}

export const rankList = (listId: string, weights: Weights) =>
  api<{ items: RankedItem[] }>('/rank', { method: 'POST', body: JSON.stringify({ list_id: listId, weights }) })

export const optimiseList = (listId: string, weights: Weights, extraDeliveryPenalty: number) =>
  api<{ plans: CartPlan[]; unavailable_items: string[] }>('/optimise', {
    method: 'POST',
    body: JSON.stringify({ list_id: listId, weights, extra_delivery_penalty: extraDeliveryPenalty }),
  })

// --- Vouchers (SPEC §6.2, screen 5) -------------------------------------------
export interface Voucher {
  id: string
  email_id: string
  store_name_raw: string
  store_id: string | null
  code: string | null
  discount_type: 'percent' | 'flat'
  value: number
  max_discount: number | null
  min_spend: number | null
  expiry: string | null
  applies_to_category: string | null
  confidence: number
  source: 'gmail' | 'demo'
  status: 'active' | 'used'
}

export interface VoucherScanResult {
  source: 'gmail' | 'demo'
  emails_scanned: number
  extracted_by: 'gemini' | 'seed'
  vouchers: Voucher[]
  ignored: { store_name_raw: string; code: string | null; reason: string }[]
}

export const getVouchers = () => api<{ vouchers: Voucher[] }>('/vouchers')

export const loadDemoVouchers = () => api<VoucherScanResult>('/vouchers/demo', { method: 'POST' })

/** Sends the short-lived Gmail token once; it is not kept anywhere in the app. */
export const scanGmail = (gmailAccessToken: string) =>
  api<VoucherScanResult>('/vouchers/scan', {
    method: 'POST',
    body: JSON.stringify({ gmail_access_token: gmailAccessToken }),
  })

// --- Orders (SPEC §8.4, screens 7-8) -----------------------------------------
export interface Order extends Omit<StorePlan, 'eta_minutes'> {
  order_id: string
  plan_id: string
  list_id: string | null
  payment_id: string
  status: 'placed'
  created_at: string
}

export const placeOrder = (planId: string, displayedTotal: number) =>
  api<{ orders: Order[]; grand_total: number }>('/orders', {
    method: 'POST',
    body: JSON.stringify({ plan_id: planId, approved: true, displayed_total: displayedTotal }),
  })

export const getOrders = () => api<{ orders: Order[]; grand_total: number }>('/orders')
