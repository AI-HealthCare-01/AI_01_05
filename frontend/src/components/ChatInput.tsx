import { useState, useRef, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const [isComposing, setIsComposing] = useState(false); // 한글 IME 조합 중 여부
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 한글 IME 조합 중이면 Enter 무시 (이중 전송 방지)
    if (isComposing) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        display: "flex",
        alignItems: "flex-end",
        gap: 8,
        padding: "12px 16px",
        background: "#FFFFFF",
        borderTop: "1px solid #E0E0E0",
      }}
    >
      <textarea
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        placeholder="메시지를 입력하세요..."
        disabled={disabled}
        maxLength={2000}
        rows={1}
        style={{
          flex: 1,
          resize: "none",
          borderRadius: 20,
          background: "#F5F5F5",
          padding: "10px 16px",
          fontSize: 14,
          border: "1px solid #E0E0E0",
          outline: "none",
          maxHeight: 120,
          opacity: disabled ? 0.5 : 1,
        }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        style={{
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: disabled || !text.trim() ? "#C8D1BE" : "#99A988",
          color: "#FFFFFF",
          border: "none",
          cursor: disabled || !text.trim() ? "default" : "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          transition: "background 0.2s",
        }}
        aria-label="전송"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          width={20}
          height={20}
        >
          <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
        </svg>
      </button>
    </div>
  );
}
