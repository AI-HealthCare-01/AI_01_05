export const COLORS = {
  background: "#F5F5F5",
  text: "#2C2C2C",
  error: "#FF0000",
  danger: "#FF0000",
  placeholder: "#757575",
  buttonBg: "#99A988",
  button: "#99A988",
  buttonText: "#F5F5F5",
  border: "#E0E0E0",
  cardBg: "#FFFFFF",
  subText: "#888888",
  overlay: "rgba(0,0,0,0.06)",
  tabActiveBg: "#99A988",
  tabActiveText: "#F5F5F5",
  tabInactiveText: "#888888",
  selectedCellBg: "#e8f0e4",
} as const;

export const MOOD_COLORS: Record<number, string> = {
  1: "#e73a35",
  2: "#ec6a3b",
  3: "#f19a4a",
  4: "#f2c66a",
  5: "#90bde3",
  6: "#5b8fcc",
  7: "#2e67b1",
};

export const MOOD_LABELS: Record<number, string> = {
  1: "매우 나쁨",
  2: "나쁨",
  3: "조금 나쁨",
  4: "보통",
  5: "조금 좋음",
  6: "좋음",
  7: "매우 좋음",
};

export const TIME_SLOT_LABELS: Record<string, string> = {
  MORNING: "아침",
  LUNCH: "점심",
  EVENING: "저녁",
  BEDTIME: "취침 전",
};

export const WRITE_METHOD_LABELS: Record<string, string> = {
  text: "직접 입력",
  ocr: "손글씨 인식",
  chatbot: "챗봇 요약",
  direct: "직접 입력",
};
