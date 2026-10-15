import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ListEditor } from '../components/ListEditor'
import { ListInput } from '../components/ListInput'
import { Results } from '../components/Results'
import {
  getList,
  optimiseList,
  PRESETS,
  rankList,
  updateList,
  type CartPlan,
  type ListResponse,
  type RankedItem,
  type ShoppingItem,
  type Weights,
} from '../lib/api'
import { blankItem, itemDomId } from '../lib/listItems'

type MobileView = 'list' | 'results'

/** Remounts the workspace per list so "+ New list" always starts clean. */
export function WorkspaceRoute() {
  const { listId } = useParams()
  return <Workspace key={listId ?? 'new'} listId={listId} />
}

/** One screen for the whole flow: input and list on the left, results on the right (stacked on phones). */
function Workspace({ listId }: { listId?: string }) {
  const navigate = useNavigate()
  const [data, setData] = useState<ListResponse | null>(null)
  const [items, setItems] = useState<ShoppingItem[]>([])
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(Boolean(listId))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showInput, setShowInput] = useState(false)
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [mobileView, setMobileView] = useState<MobileView>('results')
  const [weights, setWeights] = useState<Weights>(PRESETS.balanced)
  const [penalty, setPenalty] = useState(30)
  const [ranked, setRanked] = useState<RankedItem[] | null>(null)
  const [plans, setPlans] = useState<CartPlan[] | null>(null)
  const [plansStale, setPlansStale] = useState(false)
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)

  const load = useCallback((res: ListResponse) => {
    setData(res)
    setItems(res.items)
    setDirty(false)
    setFocusedId(null)
    setPlansStale(true)
    setPlanError(null)
  }, [])

  // Re-rank whenever the saved list or the weights change (debounced for slider drags).
  useEffect(() => {
    if (!data) return
    let cancelled = false
    const timer = window.setTimeout(() => {
      rankList(data.list_id, weights)
        .then((res) => !cancelled && setRanked(res.items))
        .catch((e: Error) => !cancelled && setError(e.message))
    }, 200)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [data, weights])

  const changeWeights = (w: Weights) => {
    setWeights(w)
    setPlansStale(true)
  }
  const changePenalty = (p: number) => {
    setPenalty(p)
    setPlansStale(true)
  }

  const findDeals = async () => {
    if (!data) return
    setPlanning(true)
    setPlanError(null)
    try {
      const res = await optimiseList(data.list_id, weights, penalty)
      setPlans(res.plans)
      setPlansStale(false)
    } catch (e) {
      setPlanError((e as Error).message)
    } finally {
      setPlanning(false)
    }
  }

  useEffect(() => {
    if (!listId) return
    getList(listId)
      .then(load)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [listId, load])

  const missing = useMemo(
    () => new Set(data ? data.items.filter((i) => !(data.matches[i.id!] ?? []).length).map((i) => i.id!) : []),
    [data],
  )

  const edit = (next: ShoppingItem[]) => {
    setItems(next)
    setDirty(true)
  }

  const save = async (next = items) => {
    if (!data) return
    setSaving(true)
    setError(null)
    try {
      const cleaned = next
        .filter((i) => i.canonical_name.trim())
        .map((i) => ({ ...i, original_text: i.original_text || i.canonical_name }))
      load(await updateList(data.list_id, cleaned, data.detected_language))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const onParsed = (res: ListResponse) => {
    load(res)
    setShowInput(false)
    setMobileView('results')
    if (res.list_id !== listId) navigate(`/lists/${res.list_id}`)
  }

  const focusItem = (id: string) => {
    setMobileView('list')
    setFocusedId(id)
    requestAnimationFrame(() => {
      const row = document.getElementById(itemDomId(id))
      row?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      row?.querySelector('input')?.focus()
    })
  }

  const removeItem = (id: string) => {
    const next = items.filter((i) => i.id !== id)
    setItems(next)
    void save(next)
  }

  if (loading) return <p className="p-8 text-center text-stone-500">Loading your list…</p>

  // No list yet: a single, centred input card.
  if (!data) {
    return (
      <div className="mx-auto max-w-xl px-4 py-10">
        <h1 className="text-2xl font-semibold">What do you need?</h1>
        <p className="mt-1 text-stone-600">
          Type, upload, speak or snap your list. English, Tamil, Hindi or a mix.
        </p>
        {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <ListInput onParsed={onParsed} />
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-4 lg:py-6">
      {/* Phone: switch between the two panels */}
      <div className="sticky top-0 z-10 -mx-4 mb-4 bg-stone-50/95 px-4 py-2 backdrop-blur lg:hidden">
        <div role="tablist" className="grid grid-cols-2 gap-1 rounded-lg bg-stone-200 p-1 text-sm font-medium">
          {(['list', 'results'] as const).map((view) => (
            <button
              key={view}
              role="tab"
              aria-selected={mobileView === view}
              onClick={() => setMobileView(view)}
              className={`rounded-md py-1.5 ${mobileView === view ? 'bg-white shadow-sm' : 'text-stone-600'}`}
            >
              {view === 'list' ? `List (${items.length})` : `Results${missing.size ? ` · ${missing.size} ⚠` : ''}`}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* Left: the list */}
        <aside className={`${mobileView === 'list' ? 'block' : 'hidden'} lg:block`}>
          <div className="rounded-xl border border-stone-200 bg-white shadow-sm lg:sticky lg:top-4">
            <div className="flex items-center justify-between gap-2 border-b border-stone-100 px-4 py-3">
              <h1 className="font-semibold">Your list</h1>
              <span className="text-sm text-stone-500">{items.length} items</span>
            </div>

            <div className="max-h-[60vh] overflow-y-auto px-3 lg:max-h-[calc(100dvh-16rem)]">
              {items.length ? (
                <ListEditor items={items} missing={missing} focusedId={focusedId} onChange={edit} />
              ) : (
                <p className="py-6 text-center text-sm text-stone-500">Your list is empty. Add items below.</p>
              )}
            </div>

            <div className="space-y-3 border-t border-stone-100 p-3">
              {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => edit([...items, blankItem()])}
                  className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium hover:bg-stone-50"
                >
                  + Item
                </button>
                <button
                  onClick={() => setShowInput((v) => !v)}
                  className="flex-1 rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium hover:bg-stone-50"
                  aria-expanded={showInput}
                >
                  {showInput ? 'Close' : '+ Paste or upload'}
                </button>
              </div>
              {showInput && <ListInput listId={data.list_id} onParsed={onParsed} />}
              <button
                onClick={() => save()}
                disabled={!dirty || saving}
                className="w-full rounded-lg bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:bg-stone-300"
              >
                {saving ? 'Updating…' : dirty ? 'Update results' : 'Results are up to date'}
              </button>
            </div>
          </div>
        </aside>

        {/* Right: results */}
        <section className={`${mobileView === 'results' ? 'block' : 'hidden'} lg:block`}>
          <Results
            data={data}
            ranked={ranked}
            stale={dirty}
            plans={plans}
            plansStale={plansStale}
            planning={planning}
            planError={planError}
            onFindDeals={findDeals}
            onVouchersChanged={() => setPlansStale(true)}
            weights={weights}
            onWeights={changeWeights}
            penalty={penalty}
            onPenalty={changePenalty}
            onEdit={focusItem}
            onRemove={removeItem}
          />
        </section>
      </div>
    </div>
  )
}
