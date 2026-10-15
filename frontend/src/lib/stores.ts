// Display info for the four mock stores (SPEC §7). Fees and rules live in the backend.
export interface StoreInfo {
  name: string
  eta: string
  badge: string // Tailwind classes for the store chip
}

export const STORES: Record<string, StoreInfo> = {
  freshmart: { name: 'FreshMart', eta: 'Next day', badge: 'bg-emerald-100 text-emerald-800' },
  quickbasket: { name: 'QuickBasket', eta: '12 min', badge: 'bg-violet-100 text-violet-800' },
  megabazaar: { name: 'MegaBazaar', eta: '2 days', badge: 'bg-sky-100 text-sky-800' },
  kiranaconnect: { name: 'Kirana Connect', eta: '45 min', badge: 'bg-amber-100 text-amber-800' },
}

export const storeInfo = (id: string): StoreInfo => STORES[id] ?? { name: id, eta: '', badge: 'bg-stone-100 text-stone-700' }
