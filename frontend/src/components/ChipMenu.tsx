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
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        overflowX: "auto",
        padding: "8px 16px",
        scrollbarWidth: "none",
      }}
    >
      {QUICK_QUESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onChipClick(q)}
          disabled={disabled}
          style={{
            flexShrink: 0,
            whiteSpace: "nowrap",
            borderRadius: 20,
            border: "1px solid #C8D1BE",
            background: "#F0F5F0",
            padding: "6px 14px",
            fontSize: 13,
            color: "#6B7F5E",
            cursor: disabled ? "default" : "pointer",
            opacity: disabled ? 0.4 : 1,
            transition: "background 0.2s",
          }}
        >
          {q}
        </button>
      ))}
    </div>
  );
}
