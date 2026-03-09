import { apiRequest } from "./client";

export function getAppointments() {
  return apiRequest("/appointments", { method: "GET" });
}

export function createAppointment(payload: Record<string, unknown>) {
  return apiRequest("/appointments", { method: "POST", body: JSON.stringify(payload) });
}

export function getAppointmentsByDate(date: string) {
  return apiRequest(`/appointments/by-date?date=${date}`, { method: "GET" });
}
