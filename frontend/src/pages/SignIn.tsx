import { useState } from 'react'
import { useAuth } from '../lib/auth-context'
import { firebaseConfigured } from '../lib/firebase'

export function SignIn() {
  const { signIn } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onClick = async () => {
    setBusy(true)
    setError(null)
    try {
      await signIn()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-6 px-4 py-16 text-center">
      <h1 className="text-3xl font-bold">CartPilot</h1>
      <p className="text-stone-600">
        Give us your shopping list in any form. We find the cheapest sensible cart across stores and your vouchers.
      </p>
      <button
        onClick={onClick}
        disabled={busy || !firebaseConfigured}
        className="w-full rounded-xl bg-brand-600 px-4 py-3 font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {busy ? 'Signing in…' : 'Sign in with Google'}
      </button>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  )
}
