import { apiRequest } from "./client";
import type { UserMe } from "../types";

export interface UpdateUserPayload {
  nickname?: string;
  email?: string | null;
  gender?: "MALE" | "FEMALE" | "UNKNOWN";
  birthday?: string | null;
}

export function getMyInfo() {
  return apiRequest<UserMe>("/users/me", { method: "GET" });
}

export function updateMyInfo(payload: UpdateUserPayload) {
  const body = Object.fromEntries(
    Object.entries(payload).filter(([, v]) => v !== "" && v !== undefined),
  );
  return apiRequest<UserMe>("/users/me", { method: "PATCH", body: JSON.stringify(body) });
}

export function deleteMyAccount() {
  return apiRequest<void>("/users/me", { method: "DELETE" });
}
