import { UNITS, type ShoppingItem, type Unit } from '../lib/api'
import { itemDomId } from '../lib/listItems'

interface Props {
  items: ShoppingItem[]
  missing: Set<string> // ids of items no store carries
  focusedId: string | null
  onChange: (items: ShoppingItem[]) => void
}

/** Compact editable list: one row per item. */
export function ListEditor({ items, missing, focusedId, onChange }: Props) {
  const update = (index: number, patch: Partial<ShoppingItem>) =>
    onChange(items.map((item, i) => (i === index ? { ...item, ...patch } : item)))

  return (
    <ul className="divide-y divide-stone-100">
      {items.map((item, index) => {
        const isMissing = Boolean(item.id && missing.has(item.id))
        const focused = Boolean(item.id && item.id === focusedId)
        return (
          <li
            key={item.id ?? `new-${index}`}
            id={item.id ? itemDomId(item.id) : undefined}
            className={`px-1 py-2.5 transition-colors ${focused ? 'rounded-lg bg-brand-50 ring-2 ring-brand-500' : ''}`}
          >
            <div className="flex items-center gap-2">
              <input
                aria-label="Item"
                value={item.canonical_name}
                onChange={(e) => update(index, { canonical_name: e.target.value })}
                placeholder="Item name"
                autoFocus={focused || (!item.id && index === items.length - 1)}
                className={`min-w-0 flex-1 rounded-md border px-2 py-1.5 text-sm ${
                  isMissing ? 'border-amber-400 bg-amber-50' : 'border-stone-300'
                }`}
              />
              <input
                aria-label="Quantity"
                type="number"
                min={0}
                step="any"
                value={item.quantity}
                onChange={(e) => update(index, { quantity: Number(e.target.value) })}
                className="w-16 rounded-md border border-stone-300 px-2 py-1.5 text-sm"
              />
              <select
                aria-label="Unit"
                value={item.unit ?? ''}
                onChange={(e) => update(index, { unit: (e.target.value || null) as Unit | null })}
                className="w-16 rounded-md border border-stone-300 px-1 py-1.5 text-sm"
              >
                <option value="">—</option>
                {UNITS.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
              <button
                aria-label={`Remove ${item.canonical_name || 'item'}`}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
                className="rounded-md px-2 py-1 text-lg leading-none text-stone-400 hover:bg-red-50 hover:text-red-700"
              >
                ×
              </button>
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 pl-0.5 text-xs text-stone-500">
              <input
                aria-label="Brand"
                value={item.brand_preference ?? ''}
                onChange={(e) => update(index, { brand_preference: e.target.value || null })}
                placeholder="Any brand"
                className="w-28 rounded border border-transparent px-1 py-0.5 hover:border-stone-300 focus:border-stone-300"
              />
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={item.optional}
                  onChange={(e) => update(index, { optional: e.target.checked })}
                />
                Optional
              </label>
              {item.original_text && item.original_text !== item.canonical_name && (
                <span className="truncate">“{item.original_text}”</span>
              )}
              {item.notes && <span className="text-amber-700">⚠ {item.notes}</span>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
