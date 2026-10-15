import { formatINR, type Candidate, type ListResponse, type ShoppingItem } from '../lib/api'
import { storeInfo } from '../lib/stores'

interface Props {
  data: ListResponse
  stale: boolean
  onEdit: (itemId: string) => void
  onRemove: (itemId: string) => void
}

const qtyLabel = (item: ShoppingItem) => `${item.quantity}${item.unit ? ` ${item.unit}` : ''}`

/** Cheapest in-stock offer per store, cheapest store first; out-of-stock stores last. */
function offersByStore(candidates: Candidate[]): Candidate[] {
  const best = new Map<string, Candidate>()
  for (const c of candidates) {
    const cur = best.get(c.store_id)
    const better =
      !cur ||
      (c.in_stock && !cur.in_stock) ||
      (c.in_stock === cur.in_stock && (c.brand_match !== cur.brand_match ? c.brand_match : c.line_price < cur.line_price))
    if (better) best.set(c.store_id, c)
  }
  return [...best.values()].sort((a, b) => Number(b.in_stock) - Number(a.in_stock) || a.line_price - b.line_price)
}

export function Results({ data, stale, onEdit, onRemove }: Props) {
  const rows = data.items.map((item) => ({ item, offers: offersByStore(data.matches[item.id!] ?? []) }))
  const missing = rows.filter((r) => r.offers.length === 0)
  const found = rows.filter((r) => r.offers.length > 0)

  return (
    <div className={stale ? 'opacity-60 transition-opacity' : ''}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">Where to buy</h2>
        <p className="text-sm text-stone-500">
          {found.length} of {rows.length} items found
          {stale && <span className="ml-2 text-brand-700">· Update to refresh</span>}
        </p>
      </div>

      {missing.length > 0 && (
        <section className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="font-medium text-amber-900">
            {missing.length === 1 ? '1 item isn’t' : `${missing.length} items aren’t`} in any of our stores
          </h3>
          <ul className="mt-2 space-y-2">
            {missing.map(({ item }) => (
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

      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        {found.map(({ item, offers }) => (
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
            <ul className="mt-3 space-y-1.5">
              {offers.map((c, i) => {
                const store = storeInfo(c.store_id)
                return (
                  <li
                    key={c.product_id}
                    className={`flex items-center gap-2 text-sm ${c.in_stock ? '' : 'text-stone-400'}`}
                    title={c.name}
                  >
                    <span className={`w-28 shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${store.badge}`}>{store.name}</span>
                    <span className="min-w-0 flex-1 truncate text-stone-600">
                      {c.qty > 1 ? `${c.qty} × ` : ''}
                      {c.pack_size}
                      {c.pack_unit === 'pcs' || c.pack_unit === 'pack' ? ` ${c.pack_unit}` : c.pack_unit}
                      <span className="ml-1 text-stone-400">★{c.rating}</span>
                    </span>
                    {c.in_stock ? (
                      <span className={`shrink-0 tabular-nums ${i === 0 ? 'font-semibold text-green-700' : ''}`}>
                        {formatINR(c.line_price)}
                      </span>
                    ) : (
                      <span className="shrink-0 text-xs">Out of stock</span>
                    )}
                  </li>
                )
              })}
            </ul>
          </article>
        ))}
      </div>
    </div>
  )
}
