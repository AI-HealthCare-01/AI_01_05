import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export function AuthRequired({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const hasTokenInUrl = Boolean(new URLSearchParams(window.location.search).get('access_token'))
  return (accessToken || hasTokenInUrl) ? <>{children}</> : <Navigate to="/" replace />
}

export function SignupRequired({ children }: { children: ReactNode }) {
  const hasTempToken = Boolean(new URLSearchParams(window.location.search).get('temp_token'))
  return hasTempToken ? <>{children}</> : <Navigate to="/" replace />
}
