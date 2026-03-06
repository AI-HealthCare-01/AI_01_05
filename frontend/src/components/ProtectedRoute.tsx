import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export function AuthRequired({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken)
  return accessToken ? <>{children}</> : <Navigate to="/" replace />
}

export function SignupRequired({ children }: { children: ReactNode }) {
  const hasTempToken = Boolean(sessionStorage.getItem('temp_token'))
  return hasTempToken ? <>{children}</> : <Navigate to="/" replace />
}
