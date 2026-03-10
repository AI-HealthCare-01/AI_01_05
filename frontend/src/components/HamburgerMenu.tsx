import { useEffect } from "react";

const HISTORY_ITEMS = [
  "현재 복용 약과 감기약 혼입 가능 여부",
  "알코올 섭취 가능 여부",
  "오늘의 일기 작성",
];

interface HamburgerMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
}

export default function HamburgerMenu({ isOpen, onClose, onNewChat }: HamburgerMenuProps) {
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
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 40,
          background: "rgba(0,0,0,0.5)",
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? "auto" : "none",
          transition: "opacity 0.3s",
        }}
        onClick={onClose}
      />

      {/* Slide panel - RIGHT side */}
      <nav
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 50,
          width: 280,
          background: "#FFFFFF",
          boxShadow: "-4px 0 20px rgba(0,0,0,0.1)",
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.3s",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            height: 56,
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
            borderBottom: "1px solid #E0E0E0",
          }}
        >
          <span style={{ fontWeight: 800, fontSize: 18, color: "#99A988" }}>도닥톡</span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: 22,
              cursor: "pointer",
              color: "#757575",
              padding: 4,
            }}
            aria-label="메뉴 닫기"
          >
            ✕
          </button>
        </div>

        {/* New chat */}
        <button
          onClick={() => {
            onNewChat();
            onClose();
          }}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            width: "100%",
            padding: "14px 16px",
            background: "none",
            border: "none",
            borderBottom: "1px solid #F0F0F0",
            cursor: "pointer",
            fontSize: 15,
            fontWeight: 700,
            color: "#99A988",
            textAlign: "left",
          }}
        >
          <span style={{ fontSize: 20 }}>+</span>
          새 채팅 시작하기
        </button>

        {/* History section */}
        <div style={{ padding: "14px 16px 8px", fontSize: 14, fontWeight: 700, color: "#757575" }}>
          = 지난 채팅 내역
        </div>
        <ul style={{ listStyle: "none", margin: 0, padding: 0, flex: 1 }}>
          {HISTORY_ITEMS.map((item) => (
            <li key={item}>
              <button
                onClick={onClose}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  width: "100%",
                  padding: "12px 16px 12px 24px",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 14,
                  color: "#2C2C2C",
                  textAlign: "left",
                }}
              >
                <span style={{ color: "#99A988" }}>•</span>
                {item}
              </button>
            </li>
          ))}
        </ul>

        {/* Footer */}
        <div
          style={{
            padding: "12px 16px",
            borderTop: "1px solid #E0E0E0",
            fontSize: 12,
            color: "#BDBDBD",
          }}
        >
          v1.0.0
        </div>
      </nav>
    </>
  );
}
