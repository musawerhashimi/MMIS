import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { GraduationCap, Loader2, Lock, User } from 'lucide-react'
import { useAuth } from '@/stores/auth'
import { errorMessage } from '@/lib/api'
import { Button } from '@/components/ui/Button'

/**
 * Sign in with a university ID.
 *
 * Not an email address: many students do not use email regularly, so the ID
 * they already know is what gets them in.
 */
export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const login = useAuth((s) => s.login)
  const loading = useAuth((s) => s.loading)
  const navigate = useNavigate()
  const [params] = useSearchParams()

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await login(username.trim(), password)
      navigate(params.get('next') ?? '/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--surface-sunken)] p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white shadow-lg shadow-brand-600/25">
            <GraduationCap className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">Monograph Management</h1>
          <p className="mt-1 text-xs text-muted">Sign in with your university ID</p>
        </div>

        <form onSubmit={submit} className="surface space-y-4 p-6 shadow-sm">
          <div>
            <label htmlFor="username" className="mb-1.5 block text-xs font-medium">
              University ID
            </label>
            <div className="relative">
              <User className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                autoFocus
                placeholder="e.g. CS-2021-001"
                className="h-10 w-full rounded-lg border bg-[var(--surface)] pl-9 pr-3 text-sm outline-none transition-colors focus:border-brand-500"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs font-medium">
              Password
            </label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="h-10 w-full rounded-lg border bg-[var(--surface)] pl-9 pr-3 text-sm outline-none transition-colors focus:border-brand-500"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <Button type="submit" size="lg" loading={loading} className="w-full justify-center">
            {loading ? 'Signing in' : 'Sign in'}
          </Button>

          <p className="text-center text-[11px] text-subtle">
            Forgotten your password? Ask the department administrator to reset it.
          </p>
        </form>
      </div>
    </div>
  )
}

/** Full-screen spinner shown while the stored session is being checked. */
export function AuthLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
    </div>
  )
}
