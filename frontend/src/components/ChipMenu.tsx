import { useState } from "react";

const QUICK_QUESTIONS = [
  "부작용이 걱정돼요",
  "약 먹는 시간이 궁금해요",
  "다른 약과 같이 먹어도 되나요?",
  "오프라벨 처방이 뭔가요?",
];

interface ChipMenuProps {
  onChipClick: (text: string) => void;
  disabled: boolean;
}

export default function ChipMenu({ onChipClick, disabled }: ChipMenuProps) {
  const [isOpen, setIsOpen] = useState(true);

  const buttonStyle = {
    borderRadius: 20,
    border: "1px solid #C8D1BE",
    background: "#F0F5F0",
    padding: "6px 14px",
    fontSize: 13,
    color: "#6B7F5E",
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.4 : 1,
    transition: "background 0.2s",
  };

  return (
    <div style={{ padding: "8px 16px" }}>
      {/* 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        style={{
          background: "transparent",
          border: "none",
          padding: "6px 0",
          fontSize: 13,
          color: "#6B7F5E",
          cursor: disabled ? "default" : "pointer",
          opacity: disabled ? 0.4 : 1,
          marginBottom: isOpen ? 8 : 0,
        }}
      >
        자주 묻는 질문 {isOpen ? "▲" : "▼"}
      </button>

      {/* 2x2 그리드 */}
      {isOpen && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
          }}
        >
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => onChipClick(q)}
              disabled={disabled}
              style={{
                ...buttonStyle,
                whiteSpace: "normal",
                textAlign: "center",
                minHeight: 40,
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
