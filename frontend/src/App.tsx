import { Navigate, Route, Routes } from 'react-router-dom'
import { HealthBadge } from './components/HealthBadge'
import { useAuth } from './lib/auth-context'
import { Home } from './pages/Home'
import { SignIn } from './pages/SignIn'

export default function App() {
  const { user, loading, signOut } = useAuth()

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-3">
        <span className="font-bold text-brand-600">CartPilot</span>
        <div className="flex items-center gap-3">
          <HealthBadge />
          {user && (
            <button onClick={signOut} className="text-sm text-stone-600 hover:text-stone-900">
              Sign out
            </button>
          )}
        </div>
      </header>
      <main>
        {loading ? (
          <p className="p-8 text-center text-stone-500">Loading…</p>
        ) : (
          <Routes>
            <Route path="/" element={user ? <Home /> : <SignIn />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </main>
    </div>
  )
}
