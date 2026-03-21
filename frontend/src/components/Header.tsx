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
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "#99A988",
          display: "flex",
          alignItems: "center",
          padding: 4,
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
        aria-label="홈으로"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      </button>

      <span style={{ fontWeight: 800, fontSize: 18, color: "#99A988" }}>
        도닥톡
      </span>

      <button
        onClick={onMenuToggle}
        style={{
          color: "#99A988",
          border: "none",
          borderRadius: 12,
          padding: "8px 14px",
          fontWeight: 400,
          cursor: "pointer",
          fontSize: 30,
          lineHeight: 1,
        }}
        aria-label="메뉴 열기"
      >
        ≡
      </button>
    </header>
  );
}
