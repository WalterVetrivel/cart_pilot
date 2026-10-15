import { useState } from 'react'
import { formatINR, type CartPlan } from '../lib/api'
import { storeInfo } from '../lib/stores'

const TITLES: Record<CartPlan['label'], string> = {
  best: 'Best value',
  single_store: 'One store',
  fastest: 'Fastest',
}

const storeKey = (p: CartPlan) => p.stores.map((s) => s.store_id).join('+')

export function PlanCards({ plans, onChoose }: { plans: CartPlan[]; onChoose?: (plan: CartPlan) => void }) {
  // When the best plan already uses one store, the "One store" card would repeat it.
  const best = plans.find((p) => p.label === 'best')
  const shown = plans.filter(
    (p) => p.label === 'best' || !best || storeKey(p) !== storeKey(best) || p.grand_total !== best.grand_total,
  )
  return (
    <div className="grid gap-3 2xl:grid-cols-3">
      {shown.map((plan) => (
        <PlanCard key={plan.plan_id} plan={plan} onChoose={onChoose} />
      ))}
    </div>
  )
}

function PlanCard({ plan, onChoose }: { plan: CartPlan; onChoose?: (plan: CartPlan) => void }) {
  const [open, setOpen] = useState(plan.label === 'best')
  const best = plan.label === 'best'
  const slowest = plan.stores.reduce((a, b) => (b.eta_minutes > a.eta_minutes ? b : a))

  return (
    <article
      className={`rounded-xl border bg-white p-4 ${best ? 'border-brand-500 ring-1 ring-brand-500' : 'border-stone-200'}`}
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-xs font-semibold uppercase tracking-wide ${best ? 'text-brand-700' : 'text-stone-500'}`}>
            {TITLES[plan.label]}
          </p>
          <p className="mt-0.5 text-2xl font-bold tabular-nums">{formatINR(plan.grand_total)}</p>
          <p className="text-xs text-stone-500">
            {plan.stores.length} {plan.stores.length === 1 ? 'delivery' : 'deliveries'} · all by {slowest.eta}
          </p>
        </div>
        {best && plan.savings_vs_single_store > 0 && (
          <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-semibold text-green-800">
            Save {formatINR(plan.savings_vs_single_store)}
          </span>
        )}
      </header>

      <p className="mt-3 font-medium">{plan.explanation.headline}</p>
      {best && plan.explanation.bullets.length > 0 && (
        <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-stone-600">
          {plan.explanation.bullets.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}

      <button onClick={() => setOpen((v) => !v)} className="mt-3 text-sm text-brand-700 hover:underline" aria-expanded={open}>
        {open ? 'Hide breakdown' : 'Show breakdown'}
      </button>

      {open && (
        <div className="mt-2 space-y-3">
          {plan.stores.map((sp) => {
            const store = storeInfo(sp.store_id)
            return (
              <section key={sp.store_id} className="rounded-lg bg-stone-50 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${store.badge}`}>{store.name}</span>
                  <span className="text-xs text-stone-500">{sp.eta}</span>
                </div>
                <ul className="mt-2 space-y-0.5">
                  {sp.lines.map((line) => (
                    <li key={line.item_id} className="flex justify-between gap-2">
                      <span className="min-w-0 truncate" title={line.name}>
                        {line.qty > 1 ? `${line.qty} × ` : ''}
                        {line.name}
                      </span>
                      <span className="shrink-0 tabular-nums">{formatINR(line.line_price)}</span>
                    </li>
                  ))}
                </ul>
                <dl className="mt-2 space-y-0.5 border-t border-stone-200 pt-2 text-stone-600">
                  <Row label="Subtotal" value={formatINR(sp.subtotal)} />
                  <Row label="Delivery" value={sp.delivery_fee ? formatINR(sp.delivery_fee) : 'Free'} />
                  {sp.voucher && (
                    <Row label={`Voucher ${sp.voucher.code ?? ''}`} value={`−${formatINR(sp.voucher.discount)}`} accent />
                  )}
                  <Row label="Total" value={formatINR(sp.total)} strong />
                </dl>
              </section>
            )
          })}
          {plan.unavailable_items.length > 0 && (
            <p className="text-xs text-amber-800">Not included: {plan.unavailable_items.join(', ')}</p>
          )}
        </div>
      )}

      <button
        onClick={() => onChoose?.(plan)}
        disabled={!onChoose}
        title={onChoose ? undefined : 'Update the plan first'}
        className={`mt-4 w-full rounded-lg px-4 py-2 text-sm font-semibold ${best ? 'bg-brand-600 text-white' : 'border border-stone-300'} disabled:opacity-50`}
      >
        Choose this plan
      </button>
    </article>
  )
}

function Row({ label, value, strong, accent }: { label: string; value: string; strong?: boolean; accent?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? 'font-semibold text-stone-900' : ''} ${accent ? 'text-green-700' : ''}`}>
      <dt>{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  )
}
