export interface ChatRequest {
  user_id: number;
  message: string;
  medication_list: string[];
  user_note?: string;
  character_id?: number | null;
  chat_history?: { role: string; content: string }[];
  message_count?: number;
  last_message_time?: string;
}

export interface ChatResponse {
  answer: string;
  warning_level: "Normal" | "Caution" | "Critical";
  red_alert: boolean;
  alert_type: "Direct" | "Indirect" | "Substance" | "Context" | null;
}

export type MessageRole = "user" | "ai";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  warningLevel?: "Normal" | "Caution" | "Critical";
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  showRedAlert: boolean;
  redAlertMessage: string | null;
  isMenuOpen: boolean;
  medicationList: string[];
}

export type ChatAction =
  | { type: "ADD_USER_MESSAGE"; payload: string }
  | { type: "ADD_AI_MESSAGE"; payload: ChatResponse }
  | { type: "START_AI_STREAM" }
  | { type: "STREAM_AI_TOKEN"; payload: string }
  | { type: "FINALIZE_AI_STREAM"; payload: { warning_level: string; red_alert: boolean; alert_type: string | null } }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SHOW_RED_ALERT"; payload: string }
  | { type: "HIDE_RED_ALERT" }
  | { type: "TOGGLE_MENU" }
  | { type: "CLOSE_MENU" }
  | { type: "SET_MEDICATIONS"; payload: string[] }
  | { type: "LOAD_HISTORY"; payload: Message[] };
