import { create } from 'zustand'

const ACCESS_TOKEN_KEY = 'access_token'

interface SelectedCharacter {
  id: number
  name: string
  imageUrl: string
}

interface AuthState {
  accessToken: string | null
  selectedCharacter: SelectedCharacter | null
  setAccessToken: (token: string) => void
  setSelectedCharacter: (c: SelectedCharacter) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  selectedCharacter: null,
  setAccessToken: (token) => set({ accessToken: token }),
  setSelectedCharacter: (c) => set({ selectedCharacter: c }),
  clearAuth: () => set({ accessToken: null, selectedCharacter: null }),
}))
