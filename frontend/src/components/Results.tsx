import { useState } from 'react'
import { formatINR, type CartPlan, type ListResponse, type RankedItem, type ShoppingItem, type Weights } from '../lib/api'
import { storeInfo } from '../lib/stores'
import { DealControls } from './DealControls'
import { ApproveDialog } from './ApproveDialog'
import { PlanCards } from './PlanCards'
import { VouchersPanel } from './VouchersPanel'

interface Props {
  data: ListResponse
  ranked: RankedItem[] | null
  stale: boolean
  plans: CartPlan[] | null
  plansStale: boolean
  planning: boolean
  planError: string | null
  onFindDeals: () => void
  onVouchersChanged: () => void
  weights: Weights
  onWeights: (w: Weights) => void
  penalty: number
  onPenalty: (p: number) => void
  onEdit: (itemId: string) => void
  onRemove: (itemId: string) => void
}

const qtyLabel = (item: ShoppingItem) => `${item.quantity}${item.unit ? ` ${item.unit}` : ''}`
const TOP_N = 3

export function Results(props: Props) {
  const { data, ranked, stale, plans, plansStale, planning, planError, onFindDeals, onEdit, onRemove } = props
  const { weights, onWeights, penalty, onPenalty, onVouchersChanged } = props
  const [choosing, setChoosing] = useState<CartPlan | null>(null)
  const byItem = new Map(ranked?.map((r) => [r.item_id, r.candidates]) ?? [])
  const missing = data.items.filter((i) => !(data.matches[i.id!] ?? []).length)
  const found = data.items.filter((i) => (data.matches[i.id!] ?? []).length)

  return (
    <div className={stale ? 'opacity-60 transition-opacity' : ''}>
      {missing.length > 0 && (
        <section className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="font-medium text-amber-900">
            {missing.length === 1 ? '1 item isn’t' : `${missing.length} items aren’t`} in any of our stores
          </h3>
          <ul className="mt-2 space-y-2">
            {missing.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 rounded-lg bg-white px-3 py-2">
                <span className="min-w-0 truncate">
                  <span className="font-medium">{item.canonical_name}</span>
                  {item.original_text && item.original_text !== item.canonical_name && (
                    <span className="ml-2 text-xs text-stone-500">“{item.original_text}”</span>
                  )}
                </span>
                <span className="flex shrink-0 gap-2 text-sm">
                  <button onClick={() => onEdit(item.id!)} className="rounded-md px-2 py-1 text-brand-700 hover:bg-brand-50">
                    Edit name
                  </button>
                  <button onClick={() => onRemove(item.id!)} className="rounded-md px-2 py-1 text-red-700 hover:bg-red-50">
                    Remove
                  </button>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-amber-800">Try a more common name, for example “wheat flour” instead of “chakki atta”.</p>
        </section>
      )}

      <VouchersPanel onChanged={onVouchersChanged} />

      {/* Cart plan */}
      <section className="rounded-xl border border-stone-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Your cart plan</h2>
            <p className="text-sm text-stone-500">
              {plans && !plansStale
                ? 'Delivery fees, minimum orders and vouchers included.'
                : 'We’ll weigh delivery fees, minimum orders and vouchers across all stores.'}
            </p>
          </div>
          {(!plans || plansStale) && (
            <button
              onClick={onFindDeals}
              disabled={planning || stale || found.length === 0}
              className="rounded-lg bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {planning ? 'Working it out…' : plans ? 'Update plan' : 'Find best deals'}
            </button>
          )}
        </div>
        <label className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-stone-600">
          <span>Each extra delivery is worth</span>
          <input
            type="range"
            min={0}
            max={200}
            step={10}
            value={penalty}
            onChange={(e) => onPenalty(Number(e.target.value))}
            className="w-32 accent-brand-600"
          />
          <span className="tabular-nums font-medium text-stone-900">₹{penalty}</span>
          <span className="text-xs text-stone-500">Higher keeps your order to fewer stores.</span>
        </label>
        {stale && <p className="mt-2 text-sm text-brand-700">Update results on the left first.</p>}
        {planError && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{planError}</p>}
        {plans && (
          <div className={`mt-4 ${plansStale ? 'opacity-50' : ''}`}>
            <PlanCards plans={plans} onChoose={plansStale || stale ? undefined : setChoosing} />
          </div>
        )}
      </section>

      {choosing && (
        <ApproveDialog
          plan={choosing}
          onClose={() => setChoosing(null)}
          onRefreshPlan={() => {
            setChoosing(null)
            onFindDeals()
          }}
        />
      )}

      {/* Per-item offers */}
      <div className="mt-6 flex items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">Top offers per item</h2>
        <p className="text-sm text-stone-500">
          {found.length} of {data.items.length} found
        </p>
      </div>
      <div className="mt-2">
        <DealControls weights={weights} onWeights={onWeights} />
      </div>
      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        {found.map((item) => {
          const offers = (byItem.get(item.id!) ?? []).filter((c) => c.in_stock).slice(0, TOP_N)
          const outOfStock = (byItem.get(item.id!) ?? []).filter((c) => !c.in_stock).length
          return (
            <article key={item.id} className="rounded-xl border border-stone-200 bg-white p-4">
              <header className="flex items-baseline justify-between gap-2">
                <button onClick={() => onEdit(item.id!)} className="truncate text-left font-medium capitalize hover:underline">
                  {item.canonical_name}
                </button>
                <span className="shrink-0 text-sm text-stone-500">
                  {qtyLabel(item)}
                  {item.optional && ' · optional'}
                </span>
              </header>
              {!ranked ? (
                <p className="mt-3 text-sm text-stone-400">Ranking…</p>
              ) : offers.length === 0 ? (
                <p className="mt-3 text-sm text-red-700">Out of stock everywhere</p>
              ) : (
                <ol className="mt-3 space-y-2">
                  {offers.map((c, i) => {
                    const store = storeInfo(c.store_id)
                    return (
                      <li key={c.product_id} className="text-sm" title={c.name}>
                        <div className="flex items-center gap-2">
                          <span className={`w-28 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${store.badge}`}>
                            {store.name}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-stone-600">
                            {c.qty > 1 ? `${c.qty} × ` : ''}
                            {c.brand} {c.pack_size}
                            {c.pack_unit === 'pcs' || c.pack_unit === 'pack' ? ` ${c.pack_unit}` : c.pack_unit}
                          </span>
                          <span className={`shrink-0 tabular-nums ${i === 0 ? 'font-semibold' : ''}`}>
                            {formatINR(c.line_price)}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-2 pl-[7.5rem] text-xs text-stone-500">
                          <span>★{c.rating}</span>
                          <span>{c.eta_label}</span>
                          <span className="ml-auto h-1.5 w-16 overflow-hidden rounded-full bg-stone-100" aria-label={`Score ${Math.round(c.score * 100)}`}>
                            <span className="block h-full bg-brand-500" style={{ width: `${Math.min(c.score, 1) * 100}%` }} />
                          </span>
                        </div>
                      </li>
                    )
                  })}
                </ol>
              )}
              {outOfStock > 0 && <p className="mt-2 text-xs text-stone-400">{outOfStock} out of stock</p>}
            </article>
          )
        })}
      </div>
    </div>
  )
}
