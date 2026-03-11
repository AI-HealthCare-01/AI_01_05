import {
  createContext,
  useContext,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";

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

    case "SET_LOADING":
      return { ...state, isLoading: action.payload };

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

    default:
      return state;
  }
}

const ChatStateContext = createContext<ChatState | null>(null);
const ChatDispatchContext = createContext<Dispatch<ChatAction> | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

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
