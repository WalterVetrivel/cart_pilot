import { formatINR, type Voucher } from './api'

const fmtDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

/** "10% off up to ₹100 · min ₹499 · staples · till 31 Dec 2026" */
export function describeVoucher(v: Voucher): string {
  const parts = [
    v.discount_type === 'percent'
      ? `${v.value}% off${v.max_discount ? ` up to ${formatINR(v.max_discount)}` : ''}`
      : `${formatINR(v.value)} off`,
  ]
  if (v.min_spend) parts.push(`min ${formatINR(v.min_spend)}`)
  if (v.applies_to_category) parts.push(`${v.applies_to_category.replace('_', ' ')} only`)
  if (v.expiry) parts.push(`till ${fmtDate(v.expiry)}`)
  return parts.join(' · ')
}
