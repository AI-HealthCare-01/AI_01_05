interface TypingIndicatorProps {
  visible: boolean;
}

export default function TypingIndicator({ visible }: TypingIndicatorProps) {
  if (!visible) return null;

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", padding: "0 16px" }}>
      <div
        style={{
          marginRight: 10,
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "rgba(107,127,94,0.15)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 16,
          flexShrink: 0,
        }}
      >
        🩺
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          borderRadius: 16,
          borderTopLeftRadius: 4,
          background: "#FFFFFF",
          border: "1px solid #E0E0E0",
          padding: "12px 16px",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#99A988",
              animation: "bounce-dot 1.4s infinite ease-in-out both",
              animationDelay: `${i * 0.16}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
