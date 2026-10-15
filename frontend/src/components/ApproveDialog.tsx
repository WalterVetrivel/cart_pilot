import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiRequestError, formatINR, placeOrder, type CartPlan } from '../lib/api'
import { storeInfo } from '../lib/stores'

// Errors that mean the plan on screen is out of date: offer to rebuild it.
const STALE = new Set(['total_changed', 'voucher_unavailable', 'out_of_stock', 'plan_not_found'])

interface Props {
  plan: CartPlan
  onClose: () => void
  onRefreshPlan: () => void
}

/** Screen 7: the only way an order is ever placed. Nothing is ordered without this tick. */
export function ApproveDialog({ plan, onClose, onRefreshPlan }: Props) {
  const navigate = useNavigate()
  const [approved, setApproved] = useState(false)
  const [placing, setPlacing] = useState(false)
  const [error, setError] = useState<ApiRequestError | Error | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !placing && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, placing])

  const place = async () => {
    setPlacing(true)
    setError(null)
    try {
      await placeOrder(plan.plan_id, plan.grand_total)
      navigate(`/orders?placed=${encodeURIComponent(plan.plan_id)}`)
    } catch (e) {
      setError(e as Error)
      setPlacing(false)
    }
  }

  const code = error instanceof ApiRequestError ? error.code : null
  const items = plan.stores.reduce((n, sp) => n + sp.lines.length, 0)

  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-stone-900/40 sm:items-center sm:p-4" onClick={() => !placing && onClose()}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="approve-title"
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90dvh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl sm:max-w-md sm:rounded-2xl"
      >
        <h2 id="approve-title" className="text-lg font-semibold">
          Approve your order
        </h2>
        <p className="mt-1 text-sm text-stone-500">
          {items} item{items === 1 ? '' : 's'} from {plan.stores.length} store{plan.stores.length === 1 ? '' : 's'}. This is a
          sandbox: no real order or payment is made.
        </p>

        <ul className="mt-4 space-y-2">
          {plan.stores.map((sp) => {
            const store = storeInfo(sp.store_id)
            return (
              <li key={sp.store_id} className="flex items-center justify-between gap-3 rounded-lg bg-stone-50 px-3 py-2 text-sm">
                <span className="min-w-0">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${store.badge}`}>{store.name}</span>
                  <span className="ml-2 text-stone-500">
                    {sp.lines.length} item{sp.lines.length === 1 ? '' : 's'} · {sp.eta}
                  </span>
                  {sp.voucher && (
                    <span className="mt-0.5 block text-xs text-green-700">
                      {sp.voucher.code} saves {formatINR(sp.voucher.discount)}
                    </span>
                  )}
                </span>
                <span className="shrink-0 font-medium tabular-nums">{formatINR(sp.total)}</span>
              </li>
            )
          })}
        </ul>

        <div className="mt-4 flex items-baseline justify-between border-t border-stone-200 pt-3">
          <span className="font-medium">Total to pay</span>
          <span className="text-2xl font-bold tabular-nums">{formatINR(plan.grand_total)}</span>
        </div>
        {plan.unavailable_items.length > 0 && (
          <p className="mt-1 text-xs text-amber-800">Not included: {plan.unavailable_items.join(', ')}</p>
        )}

        <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-lg border border-stone-300 p-3">
          <input
            type="checkbox"
            checked={approved}
            onChange={(e) => setApproved(e.target.checked)}
            className="mt-0.5 h-5 w-5 accent-brand-600"
          />
          <span className="text-sm">
            <span className="font-medium">I approve this order</span>
            <span className="block text-stone-500">for {formatINR(plan.grand_total)}, split as shown above.</span>
          </span>
        </label>

        {error && (
          <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <p>{error.message}</p>
            {code && STALE.has(code) && (
              <button onClick={onRefreshPlan} className="mt-2 font-medium underline">
                Update the plan
              </button>
            )}
            {code === 'already_ordered' && (
              <button onClick={() => navigate('/orders')} className="mt-2 font-medium underline">
                See your orders
              </button>
            )}
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <button
            onClick={onClose}
            disabled={placing}
            className="flex-1 rounded-lg border border-stone-300 px-4 py-2.5 font-medium hover:bg-stone-50 disabled:opacity-50"
          >
            Back
          </button>
          <button
            onClick={place}
            disabled={!approved || placing}
            className="flex-1 rounded-lg bg-brand-600 px-4 py-2.5 font-semibold text-white hover:bg-brand-700 disabled:bg-stone-300"
          >
            {placing ? 'Placing…' : 'Place order'}
          </button>
        </div>
      </div>
    </div>
  )
}
