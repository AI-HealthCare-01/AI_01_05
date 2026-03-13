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
