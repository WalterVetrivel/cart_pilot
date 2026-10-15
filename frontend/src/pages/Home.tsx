import { useAuth } from '../lib/auth-context'

// Placeholder for screen 2 ("Add your list"), built in milestone M1.
export function Home() {
  const { user } = useAuth()
  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h2 className="text-2xl font-semibold">Hi {user?.displayName?.split(' ')[0] ?? 'there'}</h2>
      <p className="mt-2 text-stone-600">Adding a shopping list arrives in M1.</p>
    </div>
  )
}
