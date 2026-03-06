import { COLORS } from "../constants/theme";
import { Button } from "./Button";

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <p style={{ color: COLORS.danger, fontSize: 14, margin: 0 }}>{message}</p>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          다시 시도
        </Button>
      ) : null}
    </div>
  );
}
