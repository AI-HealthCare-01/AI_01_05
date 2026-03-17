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
