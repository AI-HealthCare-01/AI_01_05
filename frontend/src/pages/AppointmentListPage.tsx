import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteAppointment, getAppointments, type AppointmentItem, updateAppointment } from "../apis/appointments";
import { Button } from "../components/Button";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { COLORS } from "../constants/theme";

function toDateLabel(appointmentDate: string): string {
  const [year, month, day] = appointmentDate.split("-").map(Number);
  if (!year || !month || !day) return "진료 일정";
  return `${month}월 ${day}일`;
}

function toTimeLabel(appointmentTime: string | null): string | null {
  if (!appointmentTime) return null;
  const [hourText, minuteText] = appointmentTime.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
  const period = hour < 12 ? "오전" : "오후";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${period} ${displayHour}:${String(minute).padStart(2, "0")}`;
}

function normalizeDateForInput(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 10);
}

function normalizeTimeForInput(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 5);
}

function toDdayLabel(appointmentDate: string): string {
  const [year, month, day] = appointmentDate.split("-").map(Number);
  if (!year || !month || !day) return "D-day";
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(year, month - 1, day);
  const diffDays = Math.floor((target.getTime() - startOfToday.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "D-day";
  return `D-${diffDays}`;
}

// ── 삭제 확인 모달 ──────────────────────────────────────────────────────────

interface DeleteModalProps {
  isOpen: boolean;
  isDeleting: boolean;
  targetLabel: string;   // 삭제 대상 표시용 (병원명 또는 날짜)
  onConfirm: () => void;
  onClose: () => void;
}

function DeleteConfirmModal({ isOpen, isDeleting, targetLabel, onConfirm, onClose }: DeleteModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // ESC 키로 닫기
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, isDeleting, onClose]);

  // 포커스 트랩
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
        <h2 id="del-modal-title" style={{ margin: 0, fontSize: 18 }}>진료 일정 삭제</h2>
        <p
          id="del-modal-desc"
          style={{ margin: 0, fontSize: 14, color: COLORS.text, lineHeight: 1.6 }}
        >
          <strong>{targetLabel}</strong> 일정을 삭제할까요?<br />
          삭제된 일정은 복구할 수 없습니다.
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

export function AppointmentListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editHospitalName, setEditHospitalName] = useState("");
  const [editAppointmentDate, setEditAppointmentDate] = useState("");
  const [editAppointmentTime, setEditAppointmentTime] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [deleteTargetItem, setDeleteTargetItem] = useState<AppointmentItem | null>(null);

  const fetchAppointments = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await getAppointments();
      setItems(response?.appointments ?? []);
    } catch {
      setError("진료 일정 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchAppointments();
  }, []);

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const aDate = new Date(a.appointment_date).getTime();
      const bDate = new Date(b.appointment_date).getTime();
      return aDate - bDate;
    });
  }, [items]);

  const remove = async (item: AppointmentItem) => {
    try {
      setDeletingId(item.appointment_id);
      setError(null);
      await deleteAppointment(item.appointment_id);
      await fetchAppointments();
    } catch {
      setError("진료 일정 삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
      setDeleteTargetItem(null);
    }
  };

  const startEdit = (item: AppointmentItem) => {
    setEditingId(item.appointment_id);
    setEditHospitalName(item.hospital_name ?? "");
    setEditAppointmentDate(normalizeDateForInput(item.appointment_date));
    setEditAppointmentTime(normalizeTimeForInput(item.appointment_time));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditHospitalName("");
    setEditAppointmentDate("");
    setEditAppointmentTime("");
  };

  const submitEdit = async (item: AppointmentItem) => {
    if (!editAppointmentDate) {
      setError("진료 날짜를 입력해주세요.");
      return;
    }
    try {
      setSavingId(item.appointment_id);
      setError(null);
      await updateAppointment(item.appointment_id, {
        hospital_name: editHospitalName.trim() || null,
        appointment_date: editAppointmentDate,
        appointment_time: editAppointmentTime || null,
      });
      await fetchAppointments();
      cancelEdit();
    } catch {
      setError("진료 일정 저장에 실패했습니다.");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "flex", justifyContent: "center" }}>
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
          padding: "16px 0",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      </button>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>진료 일정 목록</h1>
        <Button type="button" onClick={() => navigate("/appointments/new")}>
          + 일정 추가
        </Button>
      </div>

      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchAppointments()} /> : null}

      {!isLoading && sortedItems.length === 0 ? (
        <section style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16, background: "#fff", color: COLORS.subText }}>
          등록된 진료 일정이 없습니다.
        </section>
      ) : null}

      <div style={{ display: "grid", gap: 10 }}>
        {sortedItems.map((item) => {
          const dateLabel = toDateLabel(item.appointment_date);
          const timeLabel = toTimeLabel(item.appointment_time);
          return (
            <section
              key={item.appointment_id}
              style={{
                border: editingId === item.appointment_id ? "2px solid #99A988" : "1px solid #ddd",
                borderRadius: 10,
                padding: 12,
                background: "#fff",
                display: "grid",
                gap: 6,
              }}
            >
              <span
                style={{
                  width: "fit-content",
                  background: "#F0EDE3",
                  color: "#7A7040",
                  borderRadius: 999,
                  padding: "2px 10px",
                  fontSize: 12,
                  fontWeight: 700,
                  lineHeight: 1.4,
                }}
              >
                {toDdayLabel(item.appointment_date)}
              </span>
              <span style={{ fontSize: 20, fontWeight: 500, color: "#2C2C2C", lineHeight: 1.2 }}>
                {item.hospital_name ?? dateLabel}
              </span>
              <span style={{ fontSize: 13, color: "#8A8A8A", lineHeight: 1.3 }}>
                {item.hospital_name ? `${dateLabel}${timeLabel ? ` · ${timeLabel}` : ""}` : timeLabel ?? "시간 미정"}
              </span>
              <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                <button
                  type="button"
                  onClick={() => startEdit(item)}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    color: COLORS.subText,
                    textDecoration: "underline",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  수정
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteTargetItem(item)}
                  disabled={deletingId === item.appointment_id || savingId === item.appointment_id}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    color: "#C0392B",
                    textDecoration: "underline",
                    fontSize: 13,
                    cursor: deletingId === item.appointment_id ? "not-allowed" : "pointer",
                    opacity: deletingId === item.appointment_id ? 0.65 : 1,
                  }}
                >
                  {deletingId === item.appointment_id ? "삭제 중..." : "삭제"}
                </button>
              </div>
              {editingId === item.appointment_id ? (
                <div style={{ marginTop: 8, paddingTop: 10, borderTop: "1px solid #E8E8E8", display: "grid", gap: 8 }}>
                  <input
                    value={editHospitalName}
                    onChange={(event) => setEditHospitalName(event.target.value)}
                    placeholder="병원명"
                  />
                  <input
                    type="date"
                    value={editAppointmentDate}
                    onChange={(event) => setEditAppointmentDate(event.target.value)}
                  />
                  <input
                    type="time"
                    value={editAppointmentTime}
                    onChange={(event) => setEditAppointmentTime(event.target.value)}
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <Button type="button" variant="secondary" onClick={cancelEdit} disabled={savingId === item.appointment_id}>
                      취소
                    </Button>
                    <Button type="button" onClick={() => void submitEdit(item)} loading={savingId === item.appointment_id}>
                      확인
                    </Button>
                  </div>
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
      </div>

      <DeleteConfirmModal
        isOpen={deleteTargetItem !== null}
        isDeleting={deletingId === deleteTargetItem?.appointment_id}
        targetLabel={
          deleteTargetItem
            ? (deleteTargetItem.hospital_name ?? toDateLabel(deleteTargetItem.appointment_date))
            : ""
        }
        onConfirm={() => { if (deleteTargetItem) void remove(deleteTargetItem); }}
        onClose={() => { if (!deletingId) setDeleteTargetItem(null); }}
      />
    </main>
  );
}
