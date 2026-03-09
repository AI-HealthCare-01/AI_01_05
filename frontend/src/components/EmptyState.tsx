import { COLORS } from "../constants/theme";

interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div
      style={{
        padding: "24px 12px",
        borderRadius: 8,
        border: `1px solid ${COLORS.placeholder}`,
        textAlign: "center",
      }}
    >
      <p style={{ margin: 0, color: COLORS.placeholder, fontSize: 14 }}>{message}</p>
    </div>
  );
}
