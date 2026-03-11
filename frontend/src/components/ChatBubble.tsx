import type { Message } from "../types/chat";

interface ChatBubbleProps {
  message: Message;
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

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
          }}
        >
          🩺
        </div>
      )}
      <div style={bubbleStyle}>{message.content}</div>
    </div>
  );
}
