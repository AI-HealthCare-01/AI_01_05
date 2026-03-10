import { apiRequest } from "./client";
import type { MedicineDraftItem, MedicineSearchItem } from "../types/medicine";

export interface MedicineDetailItem extends MedicineSearchItem {
  efcy_qesitm: string | null;
  use_method_qesitm: string | null;
  item_image: string | null;
}

export interface UserMedicationResponse {
  medication_id: number;
  item_seq: string;
  item_name: string;
  status: string;
}

export async function searchMedicines(keyword: string, limit = 20): Promise<MedicineSearchItem[]> {
  return apiRequest<MedicineSearchItem[]>(
    `/medicines/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`
  );
}

export async function getMedicineDetail(itemSeq: string): Promise<MedicineDetailItem | null> {
  return apiRequest<MedicineDetailItem | null>(`/medicines/${itemSeq}`);
}

export async function addUserMedication(
  item: MedicineDraftItem
): Promise<UserMedicationResponse> {
  return apiRequest<UserMedicationResponse>("/user-medications", {
    method: "POST",
    body: JSON.stringify(item),
  });
}
