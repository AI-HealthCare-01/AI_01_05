import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

function addSpaceBeforeClosing(text: string): string {
  // "- **뭔가**: 설명\n일반문장" → "- **뭔가**: 설명\n\n일반문장"
  return text;
}
import type { Message } from "../types/chat";

interface ChatBubbleProps {
  message: Message;
  petImage?: string;
  isHistory?: boolean;
  onWord?: () => void;
}

function formatTime(date: Date): string {
  const h = date.getHours();
  const m = date.getMinutes().toString().padStart(2, "0");
  const period = h < 12 ? "오전" : "오후";
  const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${period} ${hour12}:${m}`;
}

export default function ChatBubble({ message, petImage, isHistory, onWord }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const [displayed, setDisplayed] = useState(isUser || isHistory ? message.content : "");
  const [animDone, setAnimDone] = useState(false);

  // 스트리밍: content가 외부에서 업데이트되면 바로 반영
  useEffect(() => {
    if (isUser || isHistory) {
      setDisplayed(message.content);
      return;
    }
    // 타이핑 애니메이션이 끝났으면 content 직접 반영 (스트리밍용)
    if (animDone) {
      setDisplayed(message.content);
      onWord?.();
      return;
    }
  }, [message.content, isUser, isHistory, animDone]);

  useEffect(() => {
    if (isUser || isHistory) return;
    setDisplayed("");
    setAnimDone(false);
    const safeContent = message.content || "";
    if (!safeContent) {
      // 스트리밍 시작 — content가 빈 상태로 시작, animDone 바로 true
      setAnimDone(true);
      return;
    }
    const words = safeContent.split(" ").filter(Boolean);
    let i = 0;
    const interval = setInterval(() => {
      if (i < words.length) {
        const total = words.length;
        const ratio = i / total;
        const chunkSize = ratio < 0.15 ? 1 : ratio < 0.30 ? 2 : ratio < 0.65 ? 3 : ratio < 0.85 ? 2 : 1;
        const chunk = words.slice(i, i + chunkSize).join(" ");
        i += chunkSize;
        setDisplayed((prev) => (prev ? prev + " " + chunk : chunk));
        onWord?.();
      } else {
        setAnimDone(true);
        clearInterval(interval);
      }
    }, 40);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isUser]);

  const bubbleBase: React.CSSProperties = {
    maxWidth: "80%",
    padding: "12px 16px",
    fontSize: 14,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    borderRadius: 16,
    lineHeight: 1.6,
  };

  let bubbleStyle: React.CSSProperties;
  if (isUser) {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 16,
      borderTopRightRadius: 4,
      borderBottomLeftRadius: 16,
      borderBottomRightRadius: 16,
      background: "#6B7F5E",
      color: "#FFFFFF",
    };
  } else if (message.warningLevel === "Critical") {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      borderTopRightRadius: 16,
      borderBottomLeftRadius: 16,
      borderBottomRightRadius: 16,
      background: "#FEF2F2",
      border: "2px solid #F87171",
      color: "#2C2C2C",
    };
  } else if (message.warningLevel === "Caution") {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      borderTopRightRadius: 16,
      borderBottomLeftRadius: 16,
      borderBottomRightRadius: 16,
      background: "#FFF7ED",
      border: "2px solid #FB923C",
      color: "#2C2C2C",
    };
  } else {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      borderTopRightRadius: 16,
      borderBottomLeftRadius: 16,
      borderBottomRightRadius: 16,
      background: "#FFFFFF",
      border: "1px solid #E0E0E0",
      color: "#2C2C2C",
    };
  }

  const timeStr = formatTime(new Date(message.timestamp));
  const timeStyle: React.CSSProperties = {
    fontSize: 11,
    color: "#999",
    whiteSpace: "nowrap",
    alignSelf: "flex-end",
    flexShrink: 0,
  };

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", padding: "0 16px" }}>
      {!isUser && (
        <div
          style={{
            marginRight: 10,
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "rgba(107,127,94,0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
            flexShrink: 0,
            overflow: "hidden",
          }}
        >
          {petImage ? (
            <img src={petImage} alt="pet" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <span>🩺</span>
          )}
        </div>
      )}

      {/* 유저 메시지: 시간 왼쪽 */}
      {isUser && <span style={{ ...timeStyle, marginRight: 6 }}>{timeStr}</span>}

      <div style={bubbleStyle}>
        {message.isStatusLoading ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 14,
                height: 14,
                border: "2px solid #D1D5DB",
                borderTopColor: "#6B7F5E",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <span style={{ fontSize: 13, color: "#6B7F5E" }}>{displayed || "정보 검색 중..."}</span>
          </div>
        ) : (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p style={{ margin: 0, marginBottom: 8, lineHeight: 1.6 }}>{children}</p>,
              ul: ({ children }) => <ul className="chat-list" style={{ margin: 0, marginTop: 2, marginBottom: 4, paddingLeft: "1.2em", listStyleType: "disc" }}>{children}</ul>,
              ol: ({ children }) => <ol className="chat-list" style={{ margin: 0, marginTop: 2, marginBottom: 4, paddingLeft: "1.2em" }}>{children}</ol>,
              li: ({ children }) => <li className="chat-li" style={{ margin: 0, padding: 0, lineHeight: 1.4 }}>{children}</li>,
              strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
              h3: ({ children }) => <strong style={{ display: "block", fontSize: 14, fontWeight: 700, marginTop: 8, marginBottom: 4 }}>{children}</strong>,
              h2: ({ children }) => <strong style={{ display: "block", fontSize: 15, fontWeight: 700, marginTop: 8, marginBottom: 4 }}>{children}</strong>,
            }}
          >
            {displayed}
          </ReactMarkdown>
        )}
      </div>

      {/* 봇 메시지: 시간 오른쪽 */}
      {!isUser && <span style={{ ...timeStyle, marginLeft: 6 }}>{timeStr}</span>}
    </div>
  );
}
