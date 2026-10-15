import type { ShoppingItem } from './api'

export const blankItem = (): ShoppingItem => ({
  canonical_name: '',
  original_text: '',
  quantity: 1,
  unit: null,
  brand_preference: null,
  category: 'other',
  notes: null,
  optional: false,
})

export const itemDomId = (id: string) => `item-${id}`
