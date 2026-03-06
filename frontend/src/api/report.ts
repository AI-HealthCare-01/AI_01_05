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
