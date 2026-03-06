import { COLORS, WRITE_METHOD_LABELS } from "../constants/theme";

interface DiaryCardData {
  title?: string;
  content?: string;
  write_method?: string;
}

interface DiaryCardProps {
  diary: DiaryCardData;
  onClick?: () => void;
}

export function DiaryCard({ diary, onClick }: DiaryCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: COLORS.cardBg,
        borderRadius: "12px",
        border: `1px solid ${COLORS.border}`,
        padding: "16px",
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
        <h3 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: COLORS.text }}>▶ {diary.title || "(제목 없음)"}</h3>
        <span
          style={{
            fontSize: "11px",
            color: COLORS.subText,
            background: COLORS.background,
            padding: "3px 8px",
            borderRadius: "20px",
            whiteSpace: "nowrap",
            marginLeft: "8px",
          }}
        >
          {WRITE_METHOD_LABELS[diary.write_method ?? ""] || diary.write_method || "직접 입력"}
        </span>
      </div>
      <p
        style={{
          margin: 0,
          fontSize: "13px",
          color: COLORS.subText,
          lineHeight: 1.6,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        }}
      >
        {diary.content}
      </p>
    </div>
  );
}

interface ReportCardData {
  reportId?: number;
  startDate?: string;
  endDate?: string;
  createdAt?: string;
  summary?: string;
}

interface ReportCardProps {
  report: ReportCardData;
  onClick?: () => void;
}

export function ReportCard({ report, onClick }: ReportCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: COLORS.cardBg,
        borderRadius: "12px",
        border: `1px solid ${COLORS.border}`,
        padding: "16px",
        cursor: onClick ? "pointer" : "default",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <span style={{ fontSize: "13px", fontWeight: 700, color: COLORS.text }}>
          {report.startDate} ~ {report.endDate}
        </span>
        <span style={{ fontSize: "11px", color: COLORS.subText }}>{report.createdAt} 생성</span>
      </div>
      <p
        style={{
          margin: 0,
          fontSize: "13px",
          color: COLORS.subText,
          lineHeight: 1.6,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        }}
      >
        {report.summary || "요약 내용 미리보기"}
      </p>
    </div>
  );
}
