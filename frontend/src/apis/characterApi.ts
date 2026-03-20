import { apiRequest } from './client'

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
  return apiRequest('/characters')
}

export function selectCharacter(character_id: number): Promise<CharacterSelectResponse> {
  return apiRequest('/characters/me', { method: 'POST', body: JSON.stringify({ character_id }) })
}

export function getMyCharacter(): Promise<CharacterSelectResponse> {
  return apiRequest('/characters/me')
}

export function changeCharacter(character_id: number): Promise<CharacterSelectResponse> {
  return apiRequest('/characters/me', { method: 'PATCH', body: JSON.stringify({ character_id }) })
}
