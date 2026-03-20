import React, { useEffect, useRef } from "react";

import { sendMessage, sendMessageStream, getChatLog } from "../apis/chatApi";
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

const DAYS = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"];

function formatDateDivider(date: Date): string {
  const y = date.getFullYear();
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const day = DAYS[date.getDay()];
  return `${y}년 ${m}월 ${d}일 ${day}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function DateDivider({ date }: { date: Date }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 16px", margin: "4px 0" }}>
      <div style={{ flex: 1, height: 1, background: "#D1D5DB" }} />
      <span style={{ fontSize: 12, color: "#9CA3AF", whiteSpace: "nowrap" }}>{formatDateDivider(date)}</span>
      <div style={{ flex: 1, height: 1, background: "#D1D5DB" }} />
    </div>
  );
}

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
    // 최근 10개 메시지로 대화 히스토리 구성
    const chatHistory = state.messages.slice(-10).map((msg) => ({
      role: msg.role === "user" ? "user" : "assistant",
      content: msg.content,
    }));

    // 친밀도 계산용: 현재 대화 메시지 수 & 마지막 메시지 시각
    const messageCount = state.messages.filter((m) => m.role === "user").length + 1;
    const lastMsg = state.messages[state.messages.length - 1];
    const lastMessageTime = lastMsg ? new Date(lastMsg.timestamp).toISOString() : undefined;

    dispatch({ type: "ADD_USER_MESSAGE", payload: text });
    dispatch({ type: "SET_LOADING", payload: true });

    const requestPayload = {
      user_id: userId!,
      message: text,
      medication_list: state.medicationList,
      character_id: selectedCharacter?.id ?? null,
      chat_history: chatHistory.length > 0 ? chatHistory : undefined,
      message_count: messageCount,
      last_message_time: lastMessageTime,
    };

    try {
      // 스트리밍으로 빈 AI 메시지 먼저 추가, 토큰 단위로 업데이트
      dispatch({ type: "START_AI_STREAM" });
      setIsHistory(false);

      await sendMessageStream(
        requestPayload,
        (token) => {
          dispatch({ type: "SET_STATUS", payload: null }); // 토큰 수신 시 상태 메시지 제거
          dispatch({ type: "STREAM_AI_TOKEN", payload: token });
        },
        (meta) => {
          dispatch({ type: "SET_STATUS", payload: null });
          dispatch({ type: "FINALIZE_AI_STREAM", payload: meta });
        },
        (status) => dispatch({ type: "SET_STATUS", payload: status }),
      );
    } catch {
      // 스트리밍 실패 시 기존 방식 폴백
      try {
        const response = await sendMessage(requestPayload);
        dispatch({ type: "ADD_AI_MESSAGE", payload: response });
      } catch {
        dispatch({
          type: "ADD_AI_MESSAGE",
          payload: {
            answer: "네트워크 연결에 문제가 있습니다. 잠시 후 다시 시도해 주세요.",
            warning_level: "Normal",
            red_alert: false,
            alert_type: null,
          },
        });
      }
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
          {state.messages.map((msg, idx) => {
            const prevMsg = idx > 0 ? state.messages[idx - 1] : null;
            const showDateDivider = !prevMsg || !isSameDay(new Date(prevMsg.timestamp), new Date(msg.timestamp));
            return (
              <React.Fragment key={msg.id}>
                {showDateDivider && <DateDivider date={new Date(msg.timestamp)} />}
                <div id={`msg-${msg.id}`}>
                  <ChatBubble
                    petImage={characterImage}
                    message={msg}
                    isHistory={isHistory}
                    onWord={idx === state.messages.length - 1 ? () => bottomRef.current?.scrollIntoView({ behavior: "smooth" }) : undefined}
                  />
                </div>
              </React.Fragment>
            );
          })}
          {state.statusMessage && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 16px" }}>
              <div
                style={{
                  width: 16,
                  height: 16,
                  border: "2px solid #D1D5DB",
                  borderTopColor: "#6B7F5E",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <span style={{ fontSize: 13, color: "#6B7F5E" }}>{state.statusMessage}</span>
            </div>
          )}
          <TypingIndicator visible={state.isLoading && !state.statusMessage} />
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
