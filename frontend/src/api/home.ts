import { apiRequest } from "./client";

export interface HomeAppointmentNextResponse {
  today: string;
  hasUpcoming: boolean;
  dDay: number | null;
  appointment: {
    appointmentId: number;
    hospitalName: string | null;
    appointmentDate: string;
    appointmentTime: string | null;
  } | null;
}

export interface HomeMoodItem {
  moodId: number;
  timeSlot: "MORNING" | "LUNCH" | "EVENING" | "BEDTIME";
  moodLevel: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  recordedAt: string;
}

export interface HomeMoodsTodayResponse {
  date: string;
  remainingSlots: Array<"MORNING" | "LUNCH" | "EVENING" | "BEDTIME">;
  moods: HomeMoodItem[];
}

export interface HomeMedicationItem {
  medicationId: number;
  itemSeq: string;
  name: string;
  timeSlot: "MORNING" | "LUNCH" | "EVENING" | "BEDTIME";
  dosePerIntake: number;
  isTaken: boolean;
  takenAt: string | null;
}

export interface HomeMedicationsTodayResponse {
  date: string;
  items: HomeMedicationItem[];
  remainingCount: number;
}

export interface HomeCreateMedicationResponse {
  medicationId: number;
  message: string;
}

export interface HomePatchMedicationResponse {
  medicationId: number;
  isTaken: boolean;
  takenAt: string | null;
  message: string;
}

export function getHomeAppointmentNext() {
  return apiRequest<HomeAppointmentNextResponse>("/home/appointments/next", { method: "GET" });
}

export function getHomeMoodsToday() {
  return apiRequest<HomeMoodsTodayResponse>("/home/moods/today", { method: "GET" });
}

export function postHomeMoodToday(payload: { timeSlot: string; moodLevel: number }) {
  return apiRequest<{ moodId: number; message: string }>("/home/moods/today", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getHomeMedicationsToday() {
  return apiRequest<HomeMedicationsTodayResponse>("/home/medications/today", { method: "GET" });
}

export function postHomeMedicationToday(payload: {
  name: string;
  timeSlot: string;
  dosage: number;
}) {
  return apiRequest<HomeCreateMedicationResponse>("/home/medications/today", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchHomeMedicationCheck(medicationId: number, isTaken: boolean) {
  return apiRequest<HomePatchMedicationResponse>(`/home/medications/today/${medicationId}/check`, {
    method: "PATCH",
    body: JSON.stringify({ isTaken }),
  });
}
