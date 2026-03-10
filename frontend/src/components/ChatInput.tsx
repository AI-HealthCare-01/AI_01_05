import { useState, useRef, type KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="sticky bottom-0 flex items-end gap-2 border-t bg-white px-4 py-3">
      <textarea
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="메시지를 입력하세요..."
        disabled={disabled}
        maxLength={2000}
        rows={1}
        className="flex-1 resize-none rounded-full bg-gray-100 px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-teal-300 disabled:opacity-50"
        style={{ maxHeight: "120px", border: "none" }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-500 text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        aria-label="전송"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-5 w-5"
        >
          <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
        </svg>
      </button>
    </div>
  );
}
