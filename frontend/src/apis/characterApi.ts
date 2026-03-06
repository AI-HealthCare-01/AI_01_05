import { useAuthStore } from '../store/authStore'

const BASE = '/api/v1'

async function authRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = useAuthStore.getState().accessToken
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string>),
    },
    credentials: 'include',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '오류가 발생했습니다.' }))
    throw { status: res.status, detail: err.detail }
  }
  return res.json()
}

export interface CharacterItem {
  character_id: number
  name: string
  description: string
  image_url: string
  personality: string | null
}

export interface CharacterSelectResponse {
  character_id: number
  name: string
  selected_at: string
}

export function getCharacters(): Promise<{ characters: CharacterItem[] }> {
  return authRequest('/characters')
}

export function selectCharacter(character_id: number): Promise<CharacterSelectResponse> {
  return authRequest('/characters/me', { method: 'POST', body: JSON.stringify({ character_id }) })
}

export function getMyCharacter(): Promise<CharacterSelectResponse> {
  return authRequest('/characters/me')
}

export function changeCharacter(character_id: number): Promise<CharacterSelectResponse> {
  return authRequest('/characters/me', { method: 'PATCH', body: JSON.stringify({ character_id }) })
}
