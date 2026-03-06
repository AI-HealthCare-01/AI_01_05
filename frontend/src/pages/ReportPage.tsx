import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Button from "../components/Button";
import { ReportCard } from "../components/Cards";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS } from "../constants/theme";
import { createReport, getReports, type ReportListItem } from "../api/report";

export function ReportPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getReports();
      setReports(data.reports ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "리포트 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchReports();
  }, [fetchReports]);

  const handleCreate = async () => {
    if (!startDate || !endDate) {
      setCreateError("시작일과 종료일을 모두 선택해주세요.");
      return;
    }
    if (startDate > endDate) {
      setCreateError("시작일이 종료일보다 늦을 수 없습니다.");
      return;
    }
    try {
      setCreateLoading(true);
      setCreateError(null);
      await createReport({ startDate, endDate });
      setStartDate("");
      setEndDate("");
      await fetchReports();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "리포트 생성에 실패했습니다.");
    } finally {
      setCreateLoading(false);
    }
  };

  const tab = location.pathname.startsWith("/report") ? "report" : "diary";

  return (
    <main style={{ minHeight: "100vh", background: COLORS.background, padding: 16, display: "grid", gap: 12 }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "15px",
          color: COLORS.subText,
          fontWeight: 600,
          padding: "0 0 16px 0",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
      </button>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0, fontSize: 22, color: COLORS.text }}>리포트</h1>
        <div
          style={{
            display: "flex",
            background: COLORS.overlay,
            borderRadius: "20px",
            padding: "4px",
            gap: "2px",
          }}
        >
          {[
            { key: "diary", label: "일기", path: "/diary" },
            { key: "report", label: "리포트", path: "/report" },
          ].map(({ key, label, path }) => (
            <button
              key={key}
              onClick={() => {
                navigate(path);
                window.scrollTo(0, 0);
              }}
              style={{
                padding: "6px 16px",
                borderRadius: "16px",
                border: "none",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                fontFamily: "inherit",
                background: tab === key ? COLORS.tabActiveBg : "transparent",
                color: tab === key ? COLORS.tabActiveText : COLORS.tabInactiveText,
                transition: "all 0.15s",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <section style={{ background: COLORS.cardBg, borderRadius: 16, border: `1px solid ${COLORS.border}`, padding: 20, display: "grid", gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 15 }}>+ 새 리포트 요약하기</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ flex: 1 }} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ flex: 1 }} />
        </div>
        {createError ? <p style={{ margin: 0, color: COLORS.error, fontSize: 13 }}>{createError}</p> : null}
        <Button variant="primary" onClick={() => void handleCreate()} loading={createLoading} fullWidth>
          요약하기
        </Button>
      </section>

      <h2 style={{ margin: "8px 0 0", fontSize: 14, color: COLORS.subText }}>= 이전 리포트 내역</h2>
      {loading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchReports()} /> : null}
      {!loading && !error && reports.length === 0 ? <EmptyState message="생성된 리포트가 없습니다." /> : null}
      {!loading && !error && reports.length > 0 ? (
        <section style={{ display: "grid", gap: 10 }}>
          {reports.map((report) => (
            <ReportCard key={report.reportId} report={report} onClick={() => navigate(`/report/${report.reportId}`)} />
          ))}
        </section>
      ) : null}
    </main>
  );
}
