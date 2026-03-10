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
    <div className="scrollbar-hide flex gap-2 overflow-x-auto px-4 py-2">
      {QUICK_QUESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onChipClick(q)}
          disabled={disabled}
          className="shrink-0 whitespace-nowrap rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-sm text-teal-700 transition-colors hover:bg-teal-100 disabled:opacity-40"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
