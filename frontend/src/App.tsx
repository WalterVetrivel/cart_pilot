import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { HealthBadge } from './components/HealthBadge'
import { useAuth } from './lib/auth-context'
import { firebaseConfigured } from './lib/firebase'
import { AddList } from './pages/AddList'
import { CheckList } from './pages/CheckList'
import { Deals } from './pages/Deals'
import { SignIn } from './pages/SignIn'

export default function App() {
  const { user, loading, signOut } = useAuth()
  // Without Firebase config the app runs as a local guest; the backend must have AUTH_DISABLED=true.
  const signedIn = Boolean(user) || !firebaseConfigured

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-3">
        <Link to="/" className="font-bold text-brand-600">
          CartPilot
        </Link>
        <div className="flex items-center gap-3">
          <HealthBadge />
          {user && (
            <button onClick={signOut} className="text-sm text-stone-600 hover:text-stone-900">
              Sign out
            </button>
          )}
        </div>
      </header>
      {!firebaseConfigured && (
        <p className="bg-amber-50 px-4 py-2 text-center text-xs text-amber-800">
          Local guest mode: Firebase isn't configured, so sign-in is skipped.
        </p>
      )}
      <main>
        {loading ? (
          <p className="p-8 text-center text-stone-500">Loading…</p>
        ) : !signedIn ? (
          <SignIn />
        ) : (
          <Routes>
            <Route path="/" element={<AddList />} />
            <Route path="/lists/:listId" element={<CheckList />} />
            <Route path="/lists/:listId/deals" element={<Deals />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
    </div>
  )
}
