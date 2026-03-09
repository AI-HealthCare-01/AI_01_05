import { COLORS } from "../constants/theme";

interface LoadingProps {
  message?: string;
}

export function Loading({ message = "로딩 중입니다..." }: LoadingProps) {
  return <p style={{ color: COLORS.placeholder, fontSize: 14 }}>{message}</p>;
}
