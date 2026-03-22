export interface DiaryEntry {
  entry_id: number;
  entry_date: string;
  title: string;
  content: string;
  ai_title?: string;
  write_method: "text" | "ocr" | "chatbot";
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface MoodLog {
  mood_id: number;
  user_id: number;
  log_date: string;
  time_slot: "MORNING" | "LUNCH" | "EVENING" | "BEDTIME";
  mood_level: 1 | 2 | 3 | 4 | 5 | 6 | 7;
  recorded_at: string;
}

export interface Report {
  report_id: number;
  user_id: number;
  start_date: string;
  end_date: string;
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface Appointment {
  appointment_id: number;
  user_id: number;
  hospital_name?: string;
  appointment_date: string;
  appointment_time?: string;
}

export interface CalendarDay {
  date: string;
  has_diary: boolean;
  moods: MoodLog[];
}

export interface UserMe {
  user_id: number;
  nickname: string;
  email: string | null;
  phone_number: string | null;
  birthday: string | null;
  gender: "MALE" | "FEMALE" | "UNKNOWN";
  created_at: string;
  onboarding_completed: boolean;
  marketing_agreed: boolean;
  sms_agreed: boolean;
}

export interface ApiError {
  message: string;
  status?: number;
}

// NOTE: OCR/Chatbot summary contracts are pending backend finalization.
// TODO: Define strict request/response types after OCR/LLM integration is finalized.
