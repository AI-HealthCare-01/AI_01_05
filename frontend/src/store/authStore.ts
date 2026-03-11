import { create } from 'zustand'

interface SelectedCharacter {
  id: number
  name: string
  imageUrl: string
}

interface AuthState {
  accessToken: string | null
  userId: number | null
  selectedCharacter: SelectedCharacter | null
  setAccessToken: (token: string) => void
  setUserId: (id: number) => void
  setSelectedCharacter: (c: SelectedCharacter) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem('access_token'),
  userId: Number(localStorage.getItem('user_id')) || null,
  selectedCharacter: null,
  setAccessToken: (token) => {
    localStorage.setItem('access_token', token)
    set({ accessToken: token })
  },
  setUserId: (id) => {
    localStorage.setItem('user_id', String(id))
    set({ userId: id })
  },
  setSelectedCharacter: (c) => set({ selectedCharacter: c }),
  clearAuth: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_id')
    set({ accessToken: null, userId: null, selectedCharacter: null })
  },
}))
