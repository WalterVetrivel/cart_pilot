import { useEffect, useState } from 'react'
import { getHealth, type Health } from '../lib/api'

export function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) {
    return <span className="rounded-full bg-red-100 px-3 py-1 text-xs text-red-700">API unreachable: {error}</span>
  }
  if (!health) {
    return <span className="rounded-full bg-stone-200 px-3 py-1 text-xs text-stone-600">Checking API…</span>
  }
  return (
    <span className="whitespace-nowrap rounded-full bg-green-100 px-3 py-1 text-xs text-green-800" title={health.model}>
      API {health.status}
      <span className="hidden sm:inline"> · {health.model}</span>
    </span>
  )
}
