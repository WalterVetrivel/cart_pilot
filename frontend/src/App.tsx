import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { HealthBadge } from './components/HealthBadge'
import { useAuth } from './lib/auth-context'
import { firebaseConfigured } from './lib/firebase'
import { Orders } from './pages/Orders'
import { SignIn } from './pages/SignIn'
import { WorkspaceRoute } from './pages/Workspace'

export default function App() {
  const { user, loading, signOut } = useAuth()
  // Without Firebase config the app runs as a local guest; the backend must have AUTH_DISABLED=true.
  const signedIn = Boolean(user) || !firebaseConfigured

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-3">
        <div className="flex items-center gap-2 sm:gap-4">
          <Link to="/" className="font-bold text-brand-600">
            CartPilot
          </Link>
          {signedIn && (
            <Link to="/" className="whitespace-nowrap rounded-lg px-2 py-1 text-sm text-stone-600 hover:bg-stone-100 hover:text-stone-900">
              + New list
            </Link>
          )}
          {signedIn && (
            <Link to="/orders" className="whitespace-nowrap rounded-lg px-2 py-1 text-sm text-stone-600 hover:bg-stone-100 hover:text-stone-900">
              Orders
            </Link>
          )}
        </div>
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
            <Route path="/" element={<WorkspaceRoute />} />
            <Route path="/lists/:listId" element={<WorkspaceRoute />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
    </div>
  )
}
