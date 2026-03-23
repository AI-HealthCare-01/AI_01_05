import { apiRequest } from "./client";

export function getMoods(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiRequest(`/moods${query}`, { method: "GET" });
}

export function createMood(payload: Record<string, unknown>) {
  return apiRequest("/moods", { method: "POST", body: JSON.stringify(payload) });
}

export function upsertMood(payload: { log_date: string; time_slot: string; mood_level: number }) {
  return apiRequest<{ message: string; data: unknown }>("/moods", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
