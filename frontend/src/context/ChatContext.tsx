import {
  createContext,
  useContext,
  useEffect,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";

import { getMyInfo } from "../apis/users";
import { useAuthStore } from "../store/authStore";
import type { ChatAction, ChatState } from "../types/chat";

const initialState: ChatState = {
  messages: [
    {
      id: "welcome",
      role: "ai",
      content:
        "안녕하세요! 도닥톡입니다 💊\n약에 대해 궁금한 점이 있으시면 편하게 물어보세요.",
      timestamp: new Date(),
      warningLevel: "Normal",
    },
  ],
  isLoading: false,
  showRedAlert: false,
  redAlertMessage: null,
  isMenuOpen: false,
  medicationList: [],
  statusMessage: null,
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "user",
            content: action.payload,
            timestamp: new Date(),
          },
        ],
      };

    case "ADD_AI_MESSAGE": {
      const response = action.payload;
      return {
        ...state,
        isLoading: false,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "ai",
            content: response.answer,
            timestamp: new Date(),
            warningLevel: response.warning_level,
          },
        ],
        showRedAlert: response.red_alert ? true : state.showRedAlert,
        redAlertMessage: response.red_alert
          ? response.answer
          : state.redAlertMessage,
      };
    }

    case "START_AI_STREAM":
      return {
        ...state,
        isLoading: false,
        messages: [
          ...state.messages,
          {
            id: crypto.randomUUID(),
            role: "ai",
            content: "",
            timestamp: new Date(),
            warningLevel: "Normal",
          },
        ],
      };

    case "STREAM_AI_TOKEN": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "ai") {
        msgs[msgs.length - 1] = { ...last, content: last.content + action.payload };
      }
      return { ...state, messages: msgs };
    }

    case "FINALIZE_AI_STREAM": {
      const msgs2 = [...state.messages];
      const last2 = msgs2[msgs2.length - 1];
      if (last2 && last2.role === "ai") {
        msgs2[msgs2.length - 1] = {
          ...last2,
          warningLevel: action.payload.warning_level as "Normal" | "Caution" | "Critical",
        };
      }
      return {
        ...state,
        messages: msgs2,
        showRedAlert: action.payload.red_alert ? true : state.showRedAlert,
        redAlertMessage: action.payload.red_alert
          ? msgs2[msgs2.length - 1]?.content || null
          : state.redAlertMessage,
      };
    }

    case "LOAD_HISTORY":
      return { ...state, messages: action.payload, isLoading: false };
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_STATUS":
      return { ...state, statusMessage: action.payload };

    case "SHOW_RED_ALERT":
      return { ...state, showRedAlert: true, redAlertMessage: action.payload };

    case "HIDE_RED_ALERT":
      return { ...state, showRedAlert: false, redAlertMessage: null };

    case "TOGGLE_MENU":
      return { ...state, isMenuOpen: !state.isMenuOpen };

    case "CLOSE_MENU":
      return { ...state, isMenuOpen: false };

    case "SET_MEDICATIONS":
      return { ...state, medicationList: action.payload };

    case "UPDATE_WELCOME": {
      const msgs = state.messages.map((m) =>
        m.id === "welcome"
          ? { ...m, content: `안녕하세요! ${action.payload}님, \n약에 대해 궁금한 점이 있으시면 편하게 물어보세요.` }
          : m
      );
      return { ...state, messages: msgs };
    }

    default:
      return state;
  }
}

const ChatStateContext = createContext<ChatState | null>(null);
const ChatDispatchContext = createContext<Dispatch<ChatAction> | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  useEffect(() => {
    const cached = useAuthStore.getState().nickname;
    if (cached) {
      dispatch({ type: "UPDATE_WELCOME", payload: cached });
      return;
    }
    getMyInfo()
      .then((u) => {
        if (u.nickname) {
          useAuthStore.getState().setNickname(u.nickname);
          dispatch({ type: "UPDATE_WELCOME", payload: u.nickname });
        }
      })
      .catch(() => {});
  }, []);

  return (
    <ChatStateContext.Provider value={state}>
      <ChatDispatchContext.Provider value={dispatch}>
        {children}
      </ChatDispatchContext.Provider>
    </ChatStateContext.Provider>
  );
}

export function useChatState(): ChatState {
  const ctx = useContext(ChatStateContext);
  if (!ctx) throw new Error("useChatState must be used within ChatProvider");
  return ctx;
}

export function useChatDispatch(): Dispatch<ChatAction> {
  const ctx = useContext(ChatDispatchContext);
  if (!ctx)
    throw new Error("useChatDispatch must be used within ChatProvider");
  return ctx;
}
