import { apiRequest } from "./client";
import type { UserMe } from "../types";

export function getMyInfo() {
  return apiRequest<UserMe>("/users/me", { method: "GET" });
}

export function updateMyInfo(payload: Partial<UserMe>) {
  return apiRequest<UserMe>("/users/me", { method: "PATCH", body: JSON.stringify(payload) });
}
