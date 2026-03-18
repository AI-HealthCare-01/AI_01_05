import { apiRequest } from "./client";

export type MedicationStatus = "ACTIVE" | "INACTIVE";

export interface UserMedicationItem {
  medication_id: number;
  item_seq: string;
  item_name: string;
  dose_per_intake: number;
  daily_frequency: number;
  total_days: number;
  start_date: string;
  status: MedicationStatus;
  time_slots: string[];
}

export interface UserMedicationsResponse {
  items: UserMedicationItem[];
}

export function getUserMedications(): Promise<UserMedicationsResponse> {
  return apiRequest<UserMedicationsResponse>("/user-medications", { method: "GET" });
}

export function deleteUserMedication(medicationId: number): Promise<void> {
  return apiRequest<void>(`/user-medications/${medicationId}`, { method: "DELETE" });
}

export interface TimeSlotsUpdateRequest {
  morning?: string;  // "HH:MM" 형식
  lunch?: string;
  dinner?: string;
  night?: string;
}

export interface TimeSlotsUpdateResponse {
  updated_count: number;
  time_slots: string[];
}

/**
 * 사용자의 모든 활성 복용약에 시간대 설정을 일괄 업데이트합니다.
 */
export function updateTimeSlots(slots: TimeSlotsUpdateRequest): Promise<TimeSlotsUpdateResponse> {
  return apiRequest<TimeSlotsUpdateResponse>("/user-medications/time-slots", {
    method: "PATCH",
    body: JSON.stringify(slots),
  });
}
