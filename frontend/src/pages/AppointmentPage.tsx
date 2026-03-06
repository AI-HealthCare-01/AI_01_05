import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createAppointment, getAppointments, getAppointmentsByDate } from "../api/appointments";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { COLORS } from "../constants/theme";

interface AppointmentItem {
  appointment_id?: number;
  hospital_name?: string;
  appointment_date?: string;
  appointment_time?: string;
}

export function AppointmentPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AppointmentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hospitalName, setHospitalName] = useState("");
  const [appointmentDate, setAppointmentDate] = useState("");
  const [appointmentTime, setAppointmentTime] = useState("");
  const [searchDate, setSearchDate] = useState("");

  const normalize = (result: unknown): AppointmentItem[] => {
    if (Array.isArray(result)) return result as AppointmentItem[];
    if (result && typeof result === "object" && "data" in result && Array.isArray((result as { data: unknown }).data)) {
      return (result as { data: AppointmentItem[] }).data;
    }
    return [];
  };

  const fetchAll = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getAppointments();
      setItems(normalize(result));
    } catch {
      setError("진료 일정을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchAll();
  }, []);

  const submit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      await createAppointment({
        hospital_name: hospitalName,
        appointment_date: appointmentDate,
        appointment_time: appointmentTime,
      });
      await fetchAll();
    } catch {
      setError("진료 일정 저장에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const searchByDate = async () => {
    if (!searchDate) return;
    try {
      setIsLoading(true);
      setError(null);
      const result = await getAppointmentsByDate(searchDate);
      setItems(normalize(result));
    } catch {
      setError("날짜별 조회에 실패했습니다.");
    } finally {
      setIsLoading(false);
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
      <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>진료 일정</h1>

      <section style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff", display: "grid", gap: 8 }}>
        <input value={hospitalName} onChange={(event) => setHospitalName(event.target.value)} placeholder="병원명" />
        <input type="date" value={appointmentDate} onChange={(event) => setAppointmentDate(event.target.value)} />
        <input type="time" value={appointmentTime} onChange={(event) => setAppointmentTime(event.target.value)} />
        <Button type="button" onClick={() => void submit()} loading={isSubmitting}>
          일정 저장
        </Button>
      </section>

      <section style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff", display: "grid", gap: 8 }}>
        <input type="date" value={searchDate} onChange={(event) => setSearchDate(event.target.value)} />
        <Button type="button" variant="secondary" onClick={() => void searchByDate()}>
          날짜별 조회
        </Button>
        <Button type="button" variant="secondary" onClick={() => void fetchAll()}>
          전체 조회
        </Button>
      </section>

      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchAll()} /> : null}
      {!isLoading && !error && items.length === 0 ? <EmptyState message="등록된 진료 일정이 없습니다." /> : null}

      {!isLoading && !error && items.length > 0 ? (
        <section style={{ display: "grid", gap: 8 }}>
          {items.map((item, index) => (
            <article
              key={`${item.appointment_id ?? "appointment"}-${index}`}
              style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff" }}
            >
              <strong>{item.hospital_name || "병원명 없음"}</strong>
              <p style={{ margin: "6px 0 0", color: COLORS.placeholder }}>
                {item.appointment_date} {item.appointment_time ?? ""}
              </p>
            </article>
          ))}
        </section>
      ) : null}
    </main>
  );
}
