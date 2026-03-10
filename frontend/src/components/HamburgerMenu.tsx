import { useEffect } from "react";

const MENU_ITEMS = [
  { icon: "💊", label: "약물 관리", path: "/medications" },
  { icon: "📋", label: "대화 기록", path: "/history" },
  { icon: "⚙️", label: "설정", path: "/settings" },
  { icon: "❓", label: "도움말", path: "/help" },
];

interface HamburgerMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function HamburgerMenu({ isOpen, onClose }: HamburgerMenuProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-300 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />

      {/* Slide panel */}
      <nav
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-white shadow-xl transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center px-4">
          <span className="text-lg font-bold text-teal-600">도닥톡</span>
        </div>

        <hr className="border-gray-200" />

        <ul className="flex-1 py-2">
          {MENU_ITEMS.map((item) => (
            <li key={item.path}>
              <button
                onClick={() => {
                  /* Phase 2: navigate(item.path) */
                  onClose();
                }}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-gray-700 hover:bg-gray-50"
              >
                <span className="text-xl">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>

        <hr className="border-gray-200" />
        <div className="px-4 py-3 text-xs text-gray-400">v1.0.0</div>
      </nav>
    </>
  );
}
