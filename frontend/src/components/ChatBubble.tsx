import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../types/chat";

interface ChatBubbleProps {
  message: Message;
  petImage?: string;
  isHistory?: boolean;
  onWord?: () => void;
}

export default function ChatBubble({ message, petImage, isHistory, onWord }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const [displayed, setDisplayed] = useState(isUser || isHistory ? message.content : "");

  useEffect(() => {
    if (isUser || isHistory) return;
    setDisplayed("");
    console.log('message.content:', JSON.stringify(message.content));
    const safeContent = message.content || "";
    const words = safeContent.split(" ").filter(Boolean);
    let i = 0;
    const interval = setInterval(() => {
      if (i < words.length) {
        const total = words.length;
        const ratio = i / total;
        const chunkSize = ratio < 0.15 ? 1 : ratio < 0.35 ? 3 : ratio < 0.65 ? 10 : ratio < 0.85 ? 3 : 1;
        const chunk = words.slice(i, i + chunkSize).join(" ");
        i += chunkSize;
        setDisplayed((prev) => (prev ? prev + " " + chunk : chunk));
        onWord?.();
      } else {
        clearInterval(interval);
      }
    }, 30);
    return () => clearInterval(interval);
  }, [message.content, isUser]);

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
    bubbleStyle = { ...bubbleBase, background: "#6B7F5E", color: "#FFFFFF" };
  } else if (message.warningLevel === "Critical") {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      background: "#FEF2F2",
      border: "2px solid #F87171",
      color: "#2C2C2C",
    };
  } else if (message.warningLevel === "Caution") {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      background: "#FFF7ED",
      border: "2px solid #FB923C",
      color: "#2C2C2C",
    };
  } else {
    bubbleStyle = {
      ...bubbleBase,
      borderTopLeftRadius: 4,
      background: "#FFFFFF",
      border: "1px solid #E0E0E0",
      color: "#2C2C2C",
    };
  }

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
      <div style={bubbleStyle}>
        <ReactMarkdown
          components={{
            p: ({ children }) => <span style={{ display: "block", marginBottom: 4 }}>{children}</span>,
            ul: ({ children }) => <ul style={{ margin: "2px 0", paddingLeft: 16, lineHeight: 1.6 }}>{children}</ul>,
            ol: ({ children }) => <ol style={{ margin: "2px 0", paddingLeft: 16, lineHeight: 1.6 }}>{children}</ol>,
            li: ({ children }) => <li style={{ marginBottom: 1 }}>{children}</li>,
            strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
            h3: ({ children }) => <strong style={{ display: "block", fontSize: 14, fontWeight: 700, marginTop: 6 }}>{children}</strong>,
            h2: ({ children }) => <strong style={{ display: "block", fontSize: 15, fontWeight: 700, marginTop: 6 }}>{children}</strong>,
          }}
        >
          {displayed.replace(/\n{2,}/g, '\n')}
        </ReactMarkdown>
      </div>
    </div>
  );
}
