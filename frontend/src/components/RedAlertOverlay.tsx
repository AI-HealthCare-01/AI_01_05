import { createPortal } from "react-dom";

const CRISIS_CONTACTS = [
  { name: "자살예방상담전화", number: "1393", desc: "24시간" },
  { name: "정신건강위기상담", number: "1577-0199", desc: "" },
  { name: "생명의전화", number: "1588-9191", desc: "" },
];

interface RedAlertOverlayProps {
  visible: boolean;
  message: string | null;
  onClose: () => void;
}

export default function RedAlertOverlay({
  visible,
  message,
  onClose,
}: RedAlertOverlayProps) {
  if (!visible) return null;

  return createPortal(
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
        padding: 16,
      }}
      role="alertdialog"
      aria-label="위기 상황 경고"
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: 20,
          boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
          width: "100%",
          maxWidth: 360,
          padding: "28px 24px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        {/* Header */}
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 22, fontWeight: 700, color: "#DC2626", margin: "0 0 6px" }}>
            지금 많이 힘드시군요
          </p>
          <p style={{ fontSize: 13, color: "#6B7280", margin: 0 }}>
            전문가가 도와드릴 수 있습니다.
          </p>
        </div>

        {/* Crisis contacts */}
        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 10 }}>
          {CRISIS_CONTACTS.map((contact) => (
            <a
              key={contact.number}
              href={`tel:${contact.number}`}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "14px 16px",
                borderRadius: 12,
                background: "#FEF2F2",
                border: "1px solid #FECACA",
                textDecoration: "none",
              }}
            >
              <span style={{ fontSize: 13, fontWeight: 500, color: "#6B7280" }}>
                {contact.name}
                {contact.desc && (
                  <span style={{ marginLeft: 4, fontSize: 11, color: "#9CA3AF" }}>
                    ({contact.desc})
                  </span>
                )}
              </span>
              <span style={{ marginTop: 4, fontSize: 22, fontWeight: 700, color: "#DC2626" }}>
                {contact.number}
              </span>
            </a>
          ))}
        </div>

        {/* Response message */}
        {message && (
          <div
            style={{
              width: "100%",
              maxHeight: 100,
              overflowY: "auto",
              borderRadius: 8,
              background: "#F9FAFB",
              padding: 10,
              fontSize: 12,
              color: "#6B7280",
              lineHeight: 1.5,
            }}
          >
            {message}
          </div>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            padding: "10px 28px",
            borderRadius: 24,
            background: "#6B7F5E",
            color: "#FFFFFF",
            border: "none",
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          대화로 돌아가기
        </button>
      </div>
    </div>,
    document.body,
  );
}
