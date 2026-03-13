import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteAppointment, getAppointments, type AppointmentItem } from "../api/appointments";
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

export function AppointmentListPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    if (!window.confirm("진료 일정을 삭제할까요?")) return;
    try {
      setDeletingId(item.appointment_id);
      setError(null);
      await deleteAppointment(item.appointment_id);
      await fetchAppointments();
    } catch {
      setError("진료 일정 삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "grid", gap: 12 }}>
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
              style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff", display: "grid", gap: 6 }}
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
                  onClick={() => navigate(`/appointments/${item.appointment_id}/edit`, { state: { appointment: item } })}
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
                  onClick={() => void remove(item)}
                  disabled={deletingId === item.appointment_id}
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
            </section>
          );
        })}
      </div>
    </main>
  );
}
