const BASE_URL = "/api/v1";
const ACCESS_TOKEN_KEY = "access_token";

export class SessionExpiredError extends Error {
  constructor(message = "세션이 만료되었습니다. 다시 로그인해주세요.") {
    super(message);
    this.name = "SessionExpiredError";
  }
}

function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

async function refreshAccessToken(): Promise<string | null> {
  const response = await fetch(`${BASE_URL}/auth/token/refresh`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) return null;

  const data = (await response.json()) as { access_token?: string; accessToken?: string };
  const nextAccessToken = data.access_token ?? data.accessToken;
  if (!nextAccessToken) return null;

  setAccessToken(nextAccessToken);
  return nextAccessToken;
}

export type ApiRequestOptions = RequestInit & {
  retryOnUnauthorized?: boolean;
};

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { retryOnUnauthorized = true, headers, ...rest } = options;
  const accessToken = getAccessToken();
  const isFormData = rest.body instanceof FormData;

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...rest,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(headers || {}),
      },
    });
  } catch {
    throw new Error("네트워크 연결을 확인해주세요.");
  }

  if (response.status === 401 && retryOnUnauthorized) {
    const nextAccessToken = await refreshAccessToken();
    if (!nextAccessToken) {
      clearTokens();
      throw new SessionExpiredError();
    }

    const retryResponse = await fetch(`${BASE_URL}${path}`, {
      ...rest,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        Authorization: `Bearer ${nextAccessToken}`,
        ...(headers || {}),
      },
    });

    if (!retryResponse.ok) {
      const text = await retryResponse.text();
      throw new Error(text || `Request failed with status ${retryResponse.status}`);
    }

    if (retryResponse.status === 204) return undefined as T;
    return (await retryResponse.json()) as T;
  }

  if (!response.ok) {
    if (response.status === 404) {
      return null as T;
    }
    if (response.status >= 500) {
      throw new Error("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
    }
    const text = await response.text();
    throw new Error(text || "요청 처리 중 오류가 발생했습니다.");
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const tokenStorage = {
  setAccessToken,
  clearTokens,
};