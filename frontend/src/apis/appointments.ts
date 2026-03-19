import { apiRequest } from "./client";

export interface AppointmentPayload {
  appointment_date: string;
  appointment_time?: string | null;
  hospital_name?: string | null;
}

export interface AppointmentItem {
  appointment_id: number;
  appointment_date: string;
  appointment_time: string | null;
  hospital_name: string | null;
}

export function getAppointments() {
  return apiRequest<{ appointments: AppointmentItem[] }>("/appointments", { method: "GET" });
}

export function getNextAppointment() {
  return apiRequest<AppointmentItem | null>("/appointments/next", { method: "GET" });
}

export function createAppointment(payload: AppointmentPayload) {
  return apiRequest<AppointmentItem>("/appointments", { method: "POST", body: JSON.stringify(payload) });
}

export function updateAppointment(appointmentId: number, payload: AppointmentPayload) {
  return apiRequest<AppointmentItem>(`/appointments/${appointmentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAppointment(appointmentId: number) {
  return apiRequest<void>(`/appointments/${appointmentId}`, { method: "DELETE" });
}
