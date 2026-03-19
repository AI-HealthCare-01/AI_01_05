import { apiRequest } from "./client";

export interface TokenRefreshResponse {
  access_token: string;
}

export function refreshToken() {
  return apiRequest<TokenRefreshResponse>("/auth/token/refresh", { method: "GET" });
}
