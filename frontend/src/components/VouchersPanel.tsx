import { useEffect, useState } from 'react'
import { getVouchers, loadDemoVouchers, scanGmail, type Voucher, type VoucherScanResult } from '../lib/api'
import { firebaseConfigured } from '../lib/firebase'
import { requestGmailToken } from '../lib/gmail'
import { storeInfo } from '../lib/stores'
import { describeVoucher } from '../lib/vouchers'

type Busy = null | 'gmail' | 'demo'

/** Screen 5: find vouchers in Gmail (read-only) or in the demo inbox. */
export function VouchersPanel({ onChanged }: { onChanged: () => void }) {
  const [vouchers, setVouchers] = useState<Voucher[] | null>(null)
  const [scan, setScan] = useState<VoucherScanResult | null>(null)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getVouchers()
      .then((res) => setVouchers(res.vouchers))
      .catch(() => setVouchers([]))
  }, [])

  const run = async (kind: Exclude<Busy, null>) => {
    setBusy(kind)
    setError(null)
    try {
      const res = kind === 'gmail' ? await scanGmail(await requestGmailToken()) : await loadDemoVouchers()
      setScan(res)
      setVouchers(res.vouchers)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const usable = (vouchers ?? []).filter((v) => v.store_id && v.status === 'active')
  const sorted = [...(vouchers ?? [])].sort((a, b) => Number(!a.store_id) - Number(!b.store_id))

  return (
    <section className="mb-4 rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Vouchers</h2>
          <p className="text-sm text-stone-500">
            {vouchers?.length
              ? `${usable.length} usable. The best valid voucher per store goes into your plan.`
              : 'Find offers in your inbox and we’ll apply the best one per store.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => run('gmail')}
            disabled={busy !== null || !firebaseConfigured}
            title={firebaseConfigured ? 'Reads offer emails from the last 60 days. Nothing is stored except the vouchers.' : 'Sign-in is off in local guest mode'}
            className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium hover:bg-stone-50 disabled:opacity-50"
          >
            {busy === 'gmail' ? 'Reading Gmail…' : 'Connect Gmail (read-only)'}
          </button>
          <button
            onClick={() => run('demo')}
            disabled={busy !== null}
            className="rounded-lg border border-stone-300 px-3 py-2 text-sm font-medium hover:bg-stone-50 disabled:opacity-50"
          >
            {busy === 'demo' ? 'Reading demo emails…' : 'Use demo vouchers'}
          </button>
        </div>
      </div>

      {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {scan && (
        <p className="mt-3 text-xs text-stone-500">
          Read {scan.emails_scanned} {scan.source === 'gmail' ? 'Gmail' : 'demo'} email{scan.emails_scanned === 1 ? '' : 's'}
          {scan.extracted_by === 'seed' ? ' (Gemini unavailable, used the prepared demo vouchers)' : ''}.
        </p>
      )}

      {sorted.length > 0 && (
        <ul className="mt-3 divide-y divide-stone-100">
          {sorted.map((v) => {
            const store = v.store_id ? storeInfo(v.store_id) : null
            const muted = !store || v.status === 'used'
            return (
              <li key={v.id} className={`flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm ${muted ? 'text-stone-400' : ''}`}>
                <span
                  className={`w-28 shrink-0 truncate rounded px-1.5 py-0.5 text-xs font-medium ${store && !muted ? store.badge : 'bg-stone-100 text-stone-500'}`}
                  title={v.store_name_raw}
                >
                  {store?.name ?? v.store_name_raw}
                </span>
                <code className={`font-mono text-xs font-semibold ${muted ? '' : 'text-stone-900'}`}>{v.code ?? 'No code'}</code>
                <span className="min-w-0 flex-1">{describeVoucher(v)}</span>
                {!store && <span className="text-xs">Other offer, not one of our stores</span>}
                {v.status === 'used' && <span className="text-xs">Used</span>}
                {v.source === 'gmail' && <span className="text-xs text-stone-400">Gmail</span>}
              </li>
            )
          })}
        </ul>
      )}

      {scan && scan.ignored.length > 0 && (
        <details className="mt-2 text-xs text-stone-500">
          <summary className="cursor-pointer">
            {scan.ignored.length} offer{scan.ignored.length === 1 ? '' : 's'} ignored
          </summary>
          <ul className="mt-1 space-y-0.5 pl-4">
            {scan.ignored.map((i, n) => (
              <li key={n}>
                {i.store_name_raw} {i.code ?? ''}: {i.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
