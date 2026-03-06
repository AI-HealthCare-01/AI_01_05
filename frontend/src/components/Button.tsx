import type { CSSProperties, ReactNode } from "react";

import { COLORS } from "../constants/theme";

type ButtonVariant = "primary" | "secondary" | "danger";

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  type?: "button" | "submit" | "reset";
  variant?: ButtonVariant;
  style?: CSSProperties;
}

const variantStyles: Record<ButtonVariant, CSSProperties> = {
  primary: {
    backgroundColor: COLORS.button,
    color: COLORS.buttonText,
    border: "none",
  },
  secondary: {
    backgroundColor: "transparent",
    color: COLORS.text,
    border: `1px solid ${COLORS.placeholder}`,
  },
  danger: {
    backgroundColor: COLORS.danger,
    color: COLORS.buttonText,
    border: "none",
  },
};

export function Button({
  children,
  onClick,
  disabled = false,
  loading = false,
  fullWidth = false,
  type = "button",
  variant = "primary",
  style,
}: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        width: fullWidth ? "100%" : "auto",
        padding: "12px 14px",
        borderRadius: 8,
        fontSize: 14,
        cursor: disabled || loading ? "not-allowed" : "pointer",
        opacity: disabled || loading ? 0.65 : 1,
        transition: "opacity 0.2s ease",
        ...variantStyles[variant],
        ...style,
      }}
    >
      {loading ? "처리 중..." : children}
    </button>
  );
}

export default Button;
