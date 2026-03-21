import { create } from 'zustand'

interface SelectedCharacter {
  id: number
  name: string
  imageUrl: string
}

interface AuthState {
  accessToken: string | null
  userId: number | null
  nickname: string | null
  selectedCharacter: SelectedCharacter | null
  setAccessToken: (token: string) => void
  setUserId: (id: number) => void
  setNickname: (name: string) => void
  setSelectedCharacter: (c: SelectedCharacter) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem('access_token'),
  userId: Number(localStorage.getItem('user_id')) || null,
  nickname: localStorage.getItem('nickname'),
  selectedCharacter: null,
  setAccessToken: (token) => {
    localStorage.setItem('access_token', token)
    set({ accessToken: token })
  },
  setUserId: (id) => {
    localStorage.setItem('user_id', String(id))
    set({ userId: id })
  },
  setNickname: (name) => {
    localStorage.setItem('nickname', name)
    set({ nickname: name })
  },
  setSelectedCharacter: (c) => set({ selectedCharacter: c }),
  clearAuth: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('nickname')
    set({ accessToken: null, userId: null, nickname: null, selectedCharacter: null })
  },
}))
