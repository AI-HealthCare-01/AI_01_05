export interface MedicineSearchItem {
  item_seq: string;
  item_name: string;
  entp_name: string | null;
}

export interface MedicineDraftItem {
  item_seq: string;
  item_name: string;
  start_date: string;
  dose_per_intake: number;
  daily_frequency: number;
  total_days: number;
  time_slots: string[];
  meal_time_pref?: string;
}
