import type { KakaoLoginResponse, SignupRequest, PhoneSendResponse, PhoneVerifyResponse } from '../types/auth'
import { useAuthStore } from '../store/authStore'

const BASE = '/api/v1'

async function request<T>(
  path: string,
  options: RequestInit = {},
  withAuth = false,
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (withAuth) {
    const token = useAuthStore.getState().accessToken
    if (token) headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers, credentials: 'include' })

  if (res.status === 401 && retry && withAuth) {
    const refreshed = await refreshToken()
    if (refreshed) {
      return request<T>(path, options, withAuth, false)
    }
    useAuthStore.getState().clearAuth()
    window.location.href = '/'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '오류가 발생했습니다.' }))
    throw { status: res.status, detail: err.detail }
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

export async function refreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/auth/token/refresh`, { credentials: 'include' })
    if (!res.ok) return false
    const data = await res.json()
    useAuthStore.getState().setAccessToken(data.access_token)
    return true
  } catch {
    return false
  }
}

export function kakaoLogin(code: string): Promise<KakaoLoginResponse> {
  return request('/auth/kakao', { method: 'POST', body: JSON.stringify({ code }) })
}

export function kakaoSignup(body: SignupRequest, tempToken: string): Promise<{ access_token: string }> {
  return request(
    '/auth/kakao/signup',
    { method: 'POST', body: JSON.stringify(body), headers: { Authorization: `Bearer ${tempToken}` } },
  )
}

export function sendPhoneCode(phone_number: string): Promise<PhoneSendResponse> {
  return request('/auth/phone/send-code', { method: 'POST', body: JSON.stringify({ phone_number }) })
}

export function verifyPhoneCode(phone_number: string, code: string): Promise<PhoneVerifyResponse> {
  return request('/auth/phone/verify-code', { method: 'POST', body: JSON.stringify({ phone_number, code }) })
}
