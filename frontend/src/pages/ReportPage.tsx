import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Button from "../components/Button";
import { ReportCard } from "../components/Cards";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS } from "../constants/theme";
import { createReport, deleteReport, getReports, type ReportListItem } from "../apis/report";

interface DeleteModalProps {
  isOpen: boolean;
  isDeleting: boolean;
  targetLabel: string;
  onConfirm: () => void;
  onClose: () => void;
}

function DeleteConfirmModal({ isOpen, isDeleting, targetLabel, onConfirm, onClose }: DeleteModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, isDeleting, onClose]);

  useEffect(() => {
    if (!isOpen || !modalRef.current) return;
    const focusable = modalRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", trap);
    first?.focus();
    return () => document.removeEventListener("keydown", trap);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget && !isDeleting) onClose(); }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        ref={modalRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="del-modal-title"
        aria-describedby="del-modal-desc"
        style={{
          background: "#fff",
          borderRadius: 16,
          padding: 24,
          maxWidth: 320,
          width: "90%",
          display: "grid",
          gap: 16,
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <h2 id="del-modal-title" style={{ margin: 0, fontSize: 18 }}>리포트 삭제</h2>
        <p
          id="del-modal-desc"
          style={{ margin: 0, fontSize: 14, color: COLORS.text, lineHeight: 1.6 }}
        >
          <strong>{targetLabel}</strong> <br />리포트를 삭제할까요?<br />
          삭제된 리포트는 복구할 수 없습니다.
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onClose}
            disabled={isDeleting}
            autoFocus
            style={{
              flex: 1,
              padding: "12px 0",
              borderRadius: 10,
              border: `1px solid ${COLORS.border}`,
              background: "#fff",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 15,
              fontFamily: "inherit",
            }}
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            aria-busy={isDeleting}
            style={{
              flex: 1,
              padding: "12px 0",
              borderRadius: 10,
              border: "none",
              background: "#fee2e2",
              color: "#dc2626",
              cursor: isDeleting ? "not-allowed" : "pointer",
              fontWeight: 700,
              fontSize: 15,
              fontFamily: "inherit",
              opacity: isDeleting ? 0.65 : 1,
            }}
          >
            {isDeleting ? "삭제 중..." : "삭제"}
          </button>
        </div>
      </div>
    </div>
  );
}

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
  const [deleteTarget, setDeleteTarget] = useState<ReportListItem | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

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
    <main style={{ minHeight: "100vh", background: COLORS.background, padding: 16, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 460, display: "grid", gap: 12, alignContent: "start" }}>
      <button
        onClick={() => navigate("/main")}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: COLORS.text,
          display: "flex",
          alignItems: "center",
          padding: 4,
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
        aria-label="홈으로"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
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
            <div key={report.reportId} style={{ position: "relative" }}>
              <ReportCard report={report} onClick={() => navigate(`/report/${report.reportId}`)} />
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setDeleteTarget(report); }}
                style={{
                  position: "absolute",
                  top: 52,
                  right: 17,
                  background: "none",
                  border: "none",
                  padding: 0,
                  color: "#C0392B",
                  textDecoration: "underline",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                삭제
              </button>
            </div>
          ))}
        </section>
      ) : null}
      </div>

      <DeleteConfirmModal
        isOpen={deleteTarget !== null}
        isDeleting={deletingId === deleteTarget?.reportId}
        targetLabel={deleteTarget ? `${deleteTarget.startDate} ~ ${deleteTarget.endDate}` : ""}
        onConfirm={() => {
          if (!deleteTarget) return;
          setDeletingId(deleteTarget.reportId);
          void deleteReport(deleteTarget.reportId)
            .then(() => fetchReports())
            .catch(() => setError("리포트 삭제에 실패했습니다."))
            .finally(() => { setDeletingId(null); setDeleteTarget(null); });
        }}
        onClose={() => { if (!deletingId) setDeleteTarget(null); }}
      />
    </main>
  );
}
