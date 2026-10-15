import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { formatINR, getOrders, type Order } from '../lib/api'
import { storeInfo } from '../lib/stores'

interface PlanGroup {
  plan_id: string
  list_id: string | null
  created_at: string
  orders: Order[]
  total: number
}

function groupByPlan(orders: Order[]): PlanGroup[] {
  const groups = new Map<string, PlanGroup>()
  for (const o of orders) {
    const g = groups.get(o.plan_id) ?? { plan_id: o.plan_id, list_id: o.list_id, created_at: o.created_at, orders: [], total: 0 }
    g.orders.push(o)
    g.total = Math.round((g.total + o.total) * 100) / 100
    groups.set(o.plan_id, g)
  }
  return [...groups.values()].sort((a, b) => b.created_at.localeCompare(a.created_at))
}

const when = (iso: string) =>
  new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

/** Screen 8: confirmation and history. */
export function Orders() {
  const [params] = useSearchParams()
  const placed = params.get('placed')
  const [groups, setGroups] = useState<PlanGroup[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getOrders()
      .then((res) => setGroups(groupByPlan(res.orders)))
      .catch((e: Error) => setError(e.message))
  }, [])

  const confirmed = groups?.find((g) => g.plan_id === placed)

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      {confirmed && (
        <section className="mb-6 rounded-xl border border-green-300 bg-green-50 p-4">
          <h1 className="text-lg font-semibold text-green-900">Order placed: {formatINR(confirmed.total)}</h1>
          <p className="text-sm text-green-800">
            {confirmed.orders.length === 1
              ? `Delivery from ${storeInfo(confirmed.orders[0].store_id).name}: ${confirmed.orders[0].eta}.`
              : `${confirmed.orders.length} deliveries are on their way.`}{' '}
            Sandbox only: nothing was really bought or charged.
          </p>
        </section>
      )}

      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-xl font-semibold">Your orders</h2>
        <Link to="/" className="text-sm text-brand-700 hover:underline">
          + New list
        </Link>
      </div>

      {error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {!groups && !error && <p className="mt-6 text-stone-500">Loading orders…</p>}
      {groups?.length === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-stone-300 p-8 text-center text-stone-500">
          No orders yet. Pick a cart plan and approve it to place one.
        </div>
      )}

      <div className="mt-4 space-y-4">
        {groups?.map((g) => (
          <article
            key={g.plan_id}
            className={`rounded-xl border bg-white p-4 ${g.plan_id === placed ? 'border-green-400' : 'border-stone-200'}`}
          >
            <header className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-sm text-stone-500">{when(g.created_at)}</p>
              <p className="text-lg font-bold tabular-nums">{formatINR(g.total)}</p>
            </header>
            <ul className="mt-2 space-y-3">
              {g.orders.map((o) => {
                const store = storeInfo(o.store_id)
                return (
                  <li key={o.order_id} className="rounded-lg bg-stone-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="flex items-center gap-2">
                        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${store.badge}`}>{store.name}</span>
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">Placed</span>
                        <span className="text-xs text-stone-500">{o.eta}</span>
                      </span>
                      <span className="font-medium tabular-nums">{formatINR(o.total)}</span>
                    </div>
                    <p className="mt-1 text-stone-600">
                      {o.lines.map((l) => `${l.qty > 1 ? `${l.qty} × ` : ''}${l.name}`).join(', ')}
                    </p>
                    <p className="mt-1 text-xs text-stone-500">
                      Delivery {o.delivery_fee ? formatINR(o.delivery_fee) : 'free'}
                      {o.voucher && ` · ${o.voucher.code} saved ${formatINR(o.voucher.discount)}`} ·{' '}
                      <span className="font-mono">{o.payment_id.slice(0, 20)}…</span>
                    </p>
                  </li>
                )
              })}
            </ul>
            {g.list_id && (
              <Link to={`/lists/${g.list_id}`} className="mt-3 inline-block text-sm text-brand-700 hover:underline">
                Open this list
              </Link>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}
