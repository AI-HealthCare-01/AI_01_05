import { apiRequest } from "./client";

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
  moodSummary?: string | null;
  clinicianNote?: string | null;
}

export function getReports() {
  return apiRequest<{ reports: ReportListItem[] }>("/diary/report", { method: "GET" });
}

export function createReport(body: { startDate: string; endDate: string }) {
  return apiRequest<ReportDetail>("/diary/report", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getReportDetail(reportId: number) {
  return apiRequest<ReportDetail | null>(`/diary/report/${reportId}`, { method: "GET" });
}

export function deleteReport(reportId: number) {
  return apiRequest<{ message: string }>(`/diary/report/${reportId}`, { method: "DELETE" });
}