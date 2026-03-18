/**
 * timeRange.ts
 *
 * 시간대 기반 레이블 계산 유틸리티
 *
 * 책임:
 *  - 기본 시간대 정의
 *  - localStorage 저장/불러오기 (DB 미사용)
 *  - 현재 시각 → 레이블 변환 (자정 넘김 범위 처리 포함)
 */

export type UiSlot = "morning" | "lunch" | "dinner" | "night";

export interface TimeRange {
  slot: UiSlot;
  label: string;       // UI 표시용 한글 레이블
  start: string;       // "HH:MM" 형식
  end: string;         // "HH:MM" 형식 (end < start 이면 자정 넘김)
}

// ── 기본값 ──────────────────────────────────────────────────────────────────

export const DEFAULT_TIME_RANGES: TimeRange[] = [
  { slot: "morning", label: "아침",   start: "06:00", end: "10:59" },
  { slot: "lunch",   label: "점심",   start: "11:00", end: "16:59" },
  { slot: "dinner",  label: "저녁",   start: "17:00", end: "20:59" },
  { slot: "night",   label: "취침 전", start: "21:00", end: "05:59" },
];

const STORAGE_KEY = "timeRanges";

// ── localStorage 유틸 ────────────────────────────────────────────────────────

/** localStorage에서 시간대 설정을 불러옵니다. 없거나 파싱 실패 시 기본값 반환. */
export function loadTimeRanges(): TimeRange[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_TIME_RANGES;

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length !== 4) return DEFAULT_TIME_RANGES;

    // 각 항목의 형식 검증
    const validated = (parsed as TimeRange[]).every(
      (r) =>
        typeof r.slot === "string" &&
        typeof r.label === "string" &&
        isValidTimeString(r.start) &&
        isValidTimeString(r.end),
    );
    if (!validated) return DEFAULT_TIME_RANGES;

    return parsed as TimeRange[];
  } catch {
    return DEFAULT_TIME_RANGES;
  }
}

/** 시간대 설정을 localStorage에 저장합니다. */
export function saveTimeRanges(ranges: TimeRange[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ranges));
}

// ── 시간 계산 ────────────────────────────────────────────────────────────────

/**
 * "HH:MM" 형식 유효성 검사
 * - 00:00 ~ 23:59 범위만 허용
 */
export function isValidTimeString(value: string): boolean {
  if (!/^\d{2}:\d{2}$/.test(value)) return false;
  const [h, m] = value.split(":").map(Number);
  return h >= 0 && h <= 23 && m >= 0 && m <= 59;
}

/** "HH:MM" → 분 단위 정수로 변환 */
function toMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

/**
 * 현재 시각이 주어진 시간대에 속하는지 판단합니다.
 * 자정 넘김 범위(예: 21:00 ~ 05:59)를 올바르게 처리합니다.
 */
function isInRange(nowMinutes: number, start: string, end: string): boolean {
  const s = toMinutes(start);
  const e = toMinutes(end);

  if (s <= e) {
    // 일반 범위: 예) 06:00 ~ 10:59
    return nowMinutes >= s && nowMinutes <= e;
  } else {
    // 자정 넘김 범위: 예) 21:00 ~ 05:59
    return nowMinutes >= s || nowMinutes <= e;
  }
}

/**
 * 현재 시각 기준으로 해당하는 UiSlot을 반환합니다.
 * 어느 범위에도 속하지 않으면 가장 가까운 다음 슬롯을 반환합니다.
 *
 * @param ranges - 사용할 시간대 배열 (기본값: loadTimeRanges())
 */
export function getCurrentSlot(ranges?: TimeRange[]): UiSlot {
  const r = ranges ?? loadTimeRanges();
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  const matched = r.find((range) => isInRange(nowMinutes, range.start, range.end));
  if (matched) return matched.slot;

  // 어느 범위에도 속하지 않는 공백 시간대 → 다음 슬롯의 시작 시간이 가장 가까운 것 반환
  let closest = r[0];
  let minDiff = Infinity;
  for (const range of r) {
    const s = toMinutes(range.start);
    const diff = s >= nowMinutes ? s - nowMinutes : s + 1440 - nowMinutes;
    if (diff < minDiff) {
      minDiff = diff;
      closest = range;
    }
  }
  return closest.slot;
}

/**
 * 현재 시각 기준으로 해당하는 한글 레이블을 반환합니다.
 * 예: "아침", "점심", "저녁", "취침 전"
 */
export function getCurrentLabel(ranges?: TimeRange[]): string {
  const r = ranges ?? loadTimeRanges();
  const slot = getCurrentSlot(r);
  return r.find((range) => range.slot === slot)?.label ?? "아침";
}

/**
 * UiSlot → 한글 레이블 변환 (주어진 ranges 기준)
 */
export function slotToLabel(slot: UiSlot, ranges?: TimeRange[]): string {
  const r = ranges ?? loadTimeRanges();
  return r.find((range) => range.slot === slot)?.label ?? slot;
}
