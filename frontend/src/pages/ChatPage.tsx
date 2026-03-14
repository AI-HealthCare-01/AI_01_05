import React, { useEffect, useRef } from "react";

import { sendMessage, getChatLog } from "../api/chatApi";
import ChatBubble from "../components/ChatBubble";
import ChatInput from "../components/ChatInput";
import ChipMenu from "../components/ChipMenu";
import HamburgerMenu from "../components/HamburgerMenu";
import Header from "../components/Header";
import RedAlertOverlay from "../components/RedAlertOverlay";
import TypingIndicator from "../components/TypingIndicator";
import { useChatDispatch, useChatState } from "../context/ChatContext";
import { useAuthStore } from "../store/authStore";
import { CHARACTER_IMAGE_BY_ID, DEFAULT_CHARACTER_IMAGE } from "../constants/characters";

export default function ChatPage() {
  const state = useChatState();
  const dispatch = useChatDispatch();
  const userId = useAuthStore((s) => s.userId);
  const selectedCharacter = useAuthStore((s) => s.selectedCharacter);
  const characterImage = CHARACTER_IMAGE_BY_ID[selectedCharacter?.id ?? 0] ?? DEFAULT_CHARACTER_IMAGE;
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isHistory, setIsHistory] = React.useState(false);

  // Auto-scroll on new message or loading change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.isLoading]);

  const handleSelectSession = async (id: number) => {
    try {
      const data = await getChatLog(id);
      const messages: import("../types/chat").Message[] = [];
      for (const log of data.messages) {
        messages.push({
          id: `user-${log.id}`,
          role: "user" as const,
          content: log.message_content,
          timestamp: new Date(),
        });
        messages.push({
          id: `ai-${log.id}`,
          role: "ai" as const,
          content: log.response_content,
          timestamp: new Date(),
          warningLevel: "Normal" as const,
        });
      }
      setIsHistory(true);
      dispatch({ type: "LOAD_HISTORY", payload: messages });
      // 타겟 메시지로 스크롤
      setTimeout(() => {
        const el = document.getElementById(`msg-user-${id}`);
        if (el) el.scrollIntoView({ behavior: "instant", block: "start" });
      }, 100);
    } catch {
      console.error("채팅 내역 불러오기 실패");
    }
  };

  const handleSend = async (text: string) => {
    dispatch({ type: "ADD_USER_MESSAGE", payload: text });
    dispatch({ type: "SET_LOADING", payload: true });

    try {
      const response = await sendMessage({
        user_id: userId!,
        message: text,
        medication_list: state.medicationList,
        character_id: selectedCharacter?.id ?? null,
      });
      setIsHistory(false);
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
    setIsHistory(false);
    window.location.reload();
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", height: "100dvh", background: "#F5F5F5" }}>
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        width: "100%",
        maxWidth: 460,
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
        onSelectSession={(id) => handleSelectSession(id)}
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
          {state.messages.map((msg, idx) => (
            <div id={`msg-${msg.id}`}><ChatBubble petImage={characterImage} key={msg.id} message={msg} isHistory={isHistory} onWord={idx === state.messages.length - 1 ? () => bottomRef.current?.scrollIntoView({ behavior: "smooth" }) : undefined} /></div>
          ))}
          <TypingIndicator visible={state.isLoading} />
          <div ref={bottomRef} />
        </div>
      </div>

      {/* 맨 아래 버튼 */}
      <button
        onClick={() => bottomRef.current?.scrollIntoView({ behavior: "smooth" })}
        style={{
          position: "fixed",
          bottom: 100,
          right: state.isMenuOpen ? 340 : 20,
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: "#6B7F5E",
          color: "#fff",
          border: "none",
          cursor: "pointer",
          fontSize: 18,
          zIndex: 100,
          boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
        }}
      >
        ↓
      </button>

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
    </div>
  );
}
