import { apiRequest } from "./client";

export interface DiaryCalendarItem {
  date: string;
  hasDiary?: boolean;
  has_diary?: boolean;
  moods?: Array<{ mood_level: number; time_slot?: string }>;
  moodStickers?: Array<{ score: number; color: string; label: string }>;
}

export interface DiaryCalendarResponse {
  year: number;
  month: number;
  days: DiaryCalendarItem[];
}

export interface DiaryDetailResponse {
  date: string;
  entries: Array<{
    entryId: number;
    source: string;
    title: string;
    content: string;
    createdAt: string;
  }>;
}

export interface ReportListItem {
  reportId: number;
  startDate: string;
  endDate: string;
  createdAt: string;
}

export interface ReportDetail {
  reportId: number;
  startDate: string;
  endDate: string;
  createdAt: string;
  summary: string;
}

export function getDiaryCalendar(year: number, month: number) {
  return apiRequest<DiaryCalendarResponse>(`/diary/calendar?year=${year}&month=${month}`, { method: "GET" });
}

export function getDiaryByDate(entryDate: string) {
  return apiRequest<DiaryDetailResponse | null>(`/diary/${entryDate}`, { method: "GET" });
}

export function createDiaryText(entryDate: string, payload: { title: string; content: string }) {
  return apiRequest<{ entryId: number; message: string }>(`/diary/${entryDate}/text`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateDiaryEntry(entryDate: string, entryId: number, payload: { title: string; content: string }) {
  return apiRequest<{ entryId: number; message: string }>(`/diary/${entryDate}/entry/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteDiaryEntry(entryDate: string, entryId: number) {
  return apiRequest<{ message: string }>(`/diary/${entryDate}/entry/${entryId}`, {
    method: "DELETE",
  });
}

export function getReportList() {
  return apiRequest<{ reports: ReportListItem[] }>("/diary/report", { method: "GET" });
}

export function createReport(payload: { startDate: string; endDate: string }) {
  return apiRequest<ReportDetail>("/diary/report", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReportDetail(reportId: number) {
  return apiRequest<ReportDetail>(`/diary/report/${reportId}`, { method: "GET" });
}

// TODO: OCR API integration (path includes entry_date)
// POST /diary/{entry_date}/photo/ocr
// POST /diary/{entry_date}/photo/ocr/confirm
// TODO: Chatbot summary API integration (path includes entry_date)
// GET /diary/{entry_date}/chatbot/summary
// POST /diary/{entry_date}/chatbot/summary/save
