import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '@/stores/auth'
import { AuthLoading } from '@/features/auth/LoginPage'
import type { Permissions } from '@/types'

interface Props {
  children: ReactNode
  /** Extra condition beyond being signed in. */
  allow?: (p: Permissions) => boolean
}

export function ProtectedRoute({ children, allow }: Props) {
  const { user, initialised } = useAuth()
  const location = useLocation()

  if (!initialised) return <AuthLoading />

  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/login?next=${next}`} replace />
  }

  if (allow && !allow(user.permissions)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
