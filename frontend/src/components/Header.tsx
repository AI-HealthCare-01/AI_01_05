interface HeaderProps {
  onMenuToggle: () => void;
  onMedicationClick: () => void;
}

export default function Header({
  onMenuToggle,
  onMedicationClick,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between bg-white px-4 shadow-sm">
      <button
        onClick={onMenuToggle}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-xl hover:bg-gray-100"
        aria-label="메뉴 열기"
      >
        ☰
      </button>

      <h1 className="text-lg font-bold text-teal-600">DodakTalk 도닥톡</h1>

      <button
        onClick={onMedicationClick}
        className="flex h-10 w-10 items-center justify-center rounded-lg text-xl hover:bg-gray-100"
        aria-label="약물 관리"
      >
        💊
      </button>
    </header>
  );
}
