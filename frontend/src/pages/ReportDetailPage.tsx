import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getReportDetail, type ReportDetail } from "../api/report";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS } from "../constants/theme";

export function ReportDetailPage() {
  const { reportId = "" } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!reportId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getReportDetail(Number(reportId));
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "리포트 상세를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    void fetchReport();
  }, [fetchReport]);

  return (
    <main style={{ minHeight: "100vh", background: COLORS.background, padding: 16, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 460, display: "grid", gap: 12, alignContent: "start" }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "15px",
          color: COLORS.subText,
          fontWeight: 600,
          padding: "16px 0",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
      </button>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <h1 style={{ margin: 0, fontSize: 20, color: COLORS.text }}>리포트 상세</h1>
      </div>

      {loading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchReport()} /> : null}
      {!loading && !error && !report ? <EmptyState message="리포트를 찾을 수 없습니다." /> : null}

      {!loading && !error && report ? (
        <section style={{ background: COLORS.cardBg, borderRadius: 16, border: `1px solid ${COLORS.border}`, padding: 20, display: "grid", gap: 8 }}>
          <p style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>
            {report.startDate} ~ {report.endDate}
          </p>
          <p style={{ margin: 0, fontSize: 12, color: COLORS.subText }}>생성일: {report.createdAt}</p>
          <textarea value={report.summary} readOnly rows={12} style={{ width: "100%", border: `1px solid ${COLORS.border}`, borderRadius: 10, padding: 12 }} />
          <p style={{ margin: 0, fontSize: 12, color: COLORS.subText }}>리포트는 현재 생성/상세 조회만 지원합니다.</p>
        </section>
      ) : null}
      </div>
    </main>
  );
}
