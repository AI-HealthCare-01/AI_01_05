import type { ChatRequest, ChatResponse } from "../types/chat";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function sendMessage(
  request: ChatRequest,
): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function sendMessageStream(
  request: ChatRequest,
  onToken: (token: string) => void,
  onMeta: (meta: { warning_level: string; red_alert: boolean; alert_type: string | null }) => void,
): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;

        try {
          const data = JSON.parse(payload);
          if ("token" in data) {
            onToken(data.token);
          } else if ("answer" in data) {
            // 위기 키워드 — 전체 응답 한 번에
            onToken(data.answer);
            onMeta({
              warning_level: data.warning_level,
              red_alert: data.red_alert,
              alert_type: data.alert_type,
            });
            return;
          } else if ("warning_level" in data) {
            onMeta(data);
          }
        } catch {
          // JSON parse error, skip
        }
      }
    }
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function getChatHistory(userId: number): Promise<{ id: number; title: string; created_at: string }[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/history?user_id=${userId}`);
  if (!response.ok) throw new Error("Failed to fetch history");
  return response.json();
}

export async function getChatLog(logId: number): Promise<{ target_id: number; messages: { id: number; message_content: string; response_content: string }[] }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/history/${logId}`);
  if (!response.ok) throw new Error("Failed to fetch log");
  return response.json();
}
