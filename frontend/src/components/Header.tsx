import { useNavigate } from "react-router-dom";

interface HeaderProps {
  onMenuToggle: () => void;
}

export default function Header({ onMenuToggle }: HeaderProps) {
  const navigate = useNavigate();

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 30,
        display: "flex",
        height: 56,
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 16px",
        background: "#FFFFFF",
        borderBottom: "1px solid #E0E0E0",
      }}
    >
      <button
        onClick={() => navigate("/main")}
        style={{
          background: "#99A988",
          color: "#FFFFFF",
          border: "none",
          borderRadius: 12,
          padding: "8px 14px",
          fontWeight: 700,
          cursor: "pointer",
          fontSize: 14,
        }}
      >
        ← 뒤로
      </button>

      <span style={{ fontWeight: 800, fontSize: 18, color: "#99A988" }}>
        도닥톡
      </span>

      <button
        onClick={onMenuToggle}
        style={{
          background: "#99A988",
          color: "#FFFFFF",
          border: "none",
          borderRadius: 12,
          padding: "8px 14px",
          fontWeight: 700,
          cursor: "pointer",
          fontSize: 18,
          lineHeight: 1,
        }}
        aria-label="메뉴 열기"
      >
        ≡
      </button>
    </header>
  );
}
