import { useEffect, useRef } from "react";

import { sendMessage } from "../api/chatApi";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import ChipMenu from "../components/ChipMenu";
import HamburgerMenu from "../components/HamburgerMenu";
import Header from "../components/Header";
import RedAlertOverlay from "../components/RedAlertOverlay";
import TypingIndicator from "../components/TypingIndicator";
import { useChatDispatch, useChatState } from "../context/ChatContext";
import { useAuthStore } from "../store/authStore";

export default function ChatPage() {
  const state = useChatState();
  const dispatch = useChatDispatch();
  const userId = useAuthStore((s) => s.userId);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new message or loading change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.isLoading]);

  const handleSend = async (text: string) => {
    dispatch({ type: "ADD_USER_MESSAGE", payload: text });
    dispatch({ type: "SET_LOADING", payload: true });

    try {
      const response = await sendMessage({
        user_id: userId!,
        message: text,
        medication_list: state.medicationList,
      });
      dispatch({ type: "ADD_AI_MESSAGE", payload: response });
    } catch {
      dispatch({
        type: "ADD_AI_MESSAGE",
        payload: {
          answer:
            "네트워크 연결에 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
          warning_level: "Normal",
          red_alert: false,
          alert_type: null,
        },
      });
    }
  };

  const handleNewChat = () => {
    // Reset chat to initial state by reloading
    window.location.reload();
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        background: "#F5F5F5",
      }}
    >
      <Header
        onMenuToggle={() => dispatch({ type: "TOGGLE_MENU" })}
      />

      <HamburgerMenu
        isOpen={state.isMenuOpen}
        onClose={() => dispatch({ type: "CLOSE_MENU" })}
        onNewChat={handleNewChat}
      />

      {/* Message list */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div
          style={{
            maxWidth: 672,
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            padding: "16px 0",
          }}
        >
          {state.messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          <TypingIndicator visible={state.isLoading} />
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Chip menu + Input */}
      <ChipMenu
        onChipClick={handleSend}
        disabled={state.isLoading || state.showRedAlert}
      />
      <ChatInput
        onSend={handleSend}
        disabled={state.isLoading || state.showRedAlert}
      />

      {/* Red Alert overlay */}
      <RedAlertOverlay
        visible={state.showRedAlert}
        message={state.redAlertMessage}
        onClose={() => dispatch({ type: "HIDE_RED_ALERT" })}
      />
    </div>
  );
}
