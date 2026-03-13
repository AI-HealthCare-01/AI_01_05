import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  createAppointment,
  deleteAppointment,
  getNextAppointment,
  type AppointmentItem,
  updateAppointment,
} from "../api/appointments";
import { Button } from "../components/Button";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { COLORS } from "../constants/theme";

export function AppointmentPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const mode = (location.state as { mode?: "create" | "edit" } | null)?.mode ?? "edit";
  const [currentAppointment, setCurrentAppointment] = useState<AppointmentItem | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hospitalName, setHospitalName] = useState("");
  const [appointmentDate, setAppointmentDate] = useState("");
  const [appointmentTime, setAppointmentTime] = useState("");

  const fetchNext = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getNextAppointment();
      setCurrentAppointment(result);
      setHospitalName(result?.hospital_name ?? "");
      setAppointmentDate(result?.appointment_date ?? "");
      setAppointmentTime(result?.appointment_time ?? "");
    } catch {
      setError("다음 진료 일정을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (mode === "create") {
      setCurrentAppointment(null);
      setHospitalName("");
      setAppointmentDate("");
      setAppointmentTime("");
      return;
    }
    void fetchNext();
  }, [mode]);

  const submit = async () => {
    if (!appointmentDate) {
      setError("진료 날짜를 입력해주세요.");
      return;
    }
    try {
      setIsSubmitting(true);
      setError(null);
      const payload = {
        hospital_name: hospitalName,
        appointment_date: appointmentDate,
        appointment_time: appointmentTime || null,
      };
      if (currentAppointment?.appointment_id) {
        await updateAppointment(currentAppointment.appointment_id, payload);
      } else {
        await createAppointment(payload);
      }
      navigate("/main");
    } catch {
      setError("진료 일정 저장에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const remove = async () => {
    if (!currentAppointment?.appointment_id) return;
    if (!window.confirm("진료 일정을 삭제할까요?")) return;
    try {
      setIsDeleting(true);
      setError(null);
      await deleteAppointment(currentAppointment.appointment_id);
      navigate("/main");
    } catch {
      setError("진료 일정 삭제에 실패했습니다.");
    } finally {
      setIsDeleting(false);
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
        {currentAppointment?.appointment_id ? (
          <button
            type="button"
            onClick={() => void remove()}
            disabled={isDeleting}
            style={{
              background: "none",
              border: "none",
              padding: 0,
              marginTop: 4,
              color: "#C0392B",
              fontSize: 13,
              textDecoration: "underline",
              cursor: isDeleting ? "not-allowed" : "pointer",
              opacity: isDeleting ? 0.65 : 1,
              justifySelf: "start",
            }}
          >
            {isDeleting ? "삭제 중..." : "일정 삭제"}
          </button>
        ) : null}
      </section>

      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchNext()} /> : null}
    </main>
  );
}
