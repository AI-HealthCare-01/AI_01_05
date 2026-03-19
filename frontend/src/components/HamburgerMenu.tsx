import { useEffect, useState } from "react";
import { getChatHistory } from "../apis/chatApi";
import { useAuthStore } from "../store/authStore";


interface HamburgerMenuProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectSession?: (id: number, title: string) => void;
}

type HistoryItem = { id: number; title: string; created_at: string };

function groupByDate(items: HistoryItem[]): { label: string; items: HistoryItem[] }[] {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 6 * 86400000);

  const groups: Record<string, HistoryItem[]> = {};
  const order: string[] = [];

  for (const item of items) {
    const d = new Date(item.created_at);
    const itemDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    let label: string;
    if (itemDate.getTime() === today.getTime()) {
      label = "오늘";
    } else if (itemDate.getTime() === yesterday.getTime()) {
      label = "어제";
    } else if (itemDate >= weekAgo) {
      label = "이번 주";
    } else {
      label = `${d.getMonth() + 1}월 ${d.getDate()}일`;
    }
    if (!groups[label]) {
      groups[label] = [];
      order.push(label);
    }
    groups[label].push(item);
  }

  return order.map((label) => ({ label, items: groups[label] }));
}

export default function HamburgerMenu({ isOpen, onClose, onNewChat, onSelectSession }: HamburgerMenuProps) {
  const userId = useAuthStore((s) => s.userId);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    if (isOpen && userId) {
      getChatHistory(userId).then(setHistory).catch(() => {});
    }
  }, [isOpen, userId]);

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
        <ul style={{ listStyle: "none", margin: 0, padding: 0, flex: 1, overflowY: "auto" }}>
          {history.length === 0 ? (
            <li style={{ padding: "24px 16px", textAlign: "center", fontSize: 13, color: "#BDBDBD" }}>
              아직 채팅 내역이 없어요
            </li>
          ) : (
            groupByDate(history).map((group) => (
              <li key={group.label}>
                <div style={{ fontSize: 11, color: "#BDBDBD", padding: "8px 16px 4px 16px" }}>
                  {group.label}
                </div>
                {group.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => { onSelectSession?.(item.id, item.title); onClose(); }}
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
                    {item.title}
                  </button>
                ))}
              </li>
            ))
          )}
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
