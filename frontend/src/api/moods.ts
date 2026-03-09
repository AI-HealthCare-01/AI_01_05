import { apiRequest } from "./client";

export function getMoods(date?: string) {
  const query = date ? `?date=${date}` : "";
  return apiRequest(`/moods${query}`, { method: "GET" });
}

export function createMood(payload: Record<string, unknown>) {
  return apiRequest("/moods", { method: "POST", body: JSON.stringify(payload) });
}
