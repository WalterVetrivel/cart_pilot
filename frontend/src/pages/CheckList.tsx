import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { formatINR, getList, updateList, UNITS, type ListResponse, type ShoppingItem, type Unit } from '../lib/api'

const LANG: Record<string, string> = { en: 'English', ta: 'Tamil', hi: 'Hindi', mixed: 'Mixed languages', other: 'Other' }

const blankItem = (): ShoppingItem => ({
  canonical_name: '',
  original_text: '',
  quantity: 1,
  unit: null,
  brand_preference: null,
  category: 'other',
  notes: null,
  optional: false,
})

export function CheckList() {
  const { listId = '' } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<ListResponse | null>(null)
  const [items, setItems] = useState<ShoppingItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getList(listId)
      .then((res) => {
        setData(res)
        setItems(res.items)
      })
      .catch((e: Error) => setError(e.message))
  }, [listId])

  const update = (index: number, patch: Partial<ShoppingItem>) =>
    setItems((prev) => prev.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  const save = async () => {
    if (!data) return
    setSaving(true)
    setError(null)
    try {
      const cleaned = items
        .filter((i) => i.canonical_name.trim())
        .map((i) => ({ ...i, original_text: i.original_text || i.canonical_name }))
      const res = await updateList(listId, cleaned, data.detected_language)
      setData(res)
      setItems(res.items)
      navigate(`/lists/${listId}/deals`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (error && !data) return <p className="p-8 text-center text-red-700">{error}</p>
  if (!data) return <p className="p-8 text-center text-stone-500">Loading your list…</p>

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-semibold">Check the list</h1>
      <p className="mt-1 text-stone-600">
        We read {data.items.length} items ({LANG[data.detected_language] ?? data.detected_language}). Fix anything we got
        wrong.
      </p>

      {items.length === 0 && (
        <p className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800">No items found. Add them below.</p>
      )}

      <ul className="mt-6 space-y-3">
        {items.map((item, index) => {
          const matches = item.id ? data.matches[item.id] : undefined
          const cheapest = matches?.filter((m) => m.in_stock).sort((a, b) => a.line_price - b.line_price)[0]
          const stores = new Set(matches?.map((m) => m.store_id)).size
          return (
            <li key={item.id ?? `new-${index}`} className="rounded-xl border border-stone-200 bg-white p-3">
              <div className="grid grid-cols-12 gap-2">
                <input
                  aria-label="Item"
                  value={item.canonical_name}
                  onChange={(e) => update(index, { canonical_name: e.target.value })}
                  placeholder="Item"
                  className="col-span-12 rounded-lg border border-stone-300 px-2 py-1.5 sm:col-span-5"
                />
                <input
                  aria-label="Quantity"
                  type="number"
                  min={0}
                  step="any"
                  value={item.quantity}
                  onChange={(e) => update(index, { quantity: Number(e.target.value) })}
                  className="col-span-3 rounded-lg border border-stone-300 px-2 py-1.5 sm:col-span-2"
                />
                <select
                  aria-label="Unit"
                  value={item.unit ?? ''}
                  onChange={(e) => update(index, { unit: (e.target.value || null) as Unit | null })}
                  className="col-span-3 rounded-lg border border-stone-300 px-1 py-1.5 sm:col-span-2"
                >
                  <option value="">—</option>
                  {UNITS.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
                <input
                  aria-label="Brand"
                  value={item.brand_preference ?? ''}
                  onChange={(e) => update(index, { brand_preference: e.target.value || null })}
                  placeholder="Any brand"
                  className="col-span-6 rounded-lg border border-stone-300 px-2 py-1.5 sm:col-span-3"
                />
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="text-stone-500">
                  {item.original_text && <span>“{item.original_text}”</span>}
                  {item.notes && <span className="ml-2 text-amber-700">⚠ {item.notes}</span>}
                  {item.id && (
                    <span className={`ml-2 ${stores ? 'text-green-700' : 'text-red-700'}`}>
                      {stores
                        ? `${stores} store${stores > 1 ? 's' : ''}${cheapest ? ` · from ${formatINR(cheapest.line_price)}` : ''}`
                        : 'Not in our stores'}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1 text-stone-600">
                    <input
                      type="checkbox"
                      checked={item.optional}
                      onChange={(e) => update(index, { optional: e.target.checked })}
                    />
                    Optional
                  </label>
                  <button
                    onClick={() => setItems((prev) => prev.filter((_, i) => i !== index))}
                    className="text-red-700 hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          )
        })}
      </ul>

      <button
        onClick={() => setItems((prev) => [...prev, blankItem()])}
        className="mt-3 w-full rounded-xl border-2 border-dashed border-stone-300 py-2 text-stone-600 hover:border-brand-500"
      >
        + Add item
      </button>

      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <button
        onClick={save}
        disabled={saving || !items.some((i) => i.canonical_name.trim())}
        className="mt-6 w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {saving ? 'Saving…' : 'Find best deals'}
      </button>
    </div>
  )
}
