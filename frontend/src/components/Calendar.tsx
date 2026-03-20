/**
 * ┌─────────────────────────────────────────────┐
 * │  캘린더 셀 레이아웃 (모든 요소 동시 표시 시)  │
 * │                                             │
 * │   ╭──────────────────╮                      │
 * │   │ ┌─────┐          │  ← 오늘: 파란 링     │
 * │   │ │ 15  │          │  ← 날짜 숫자         │
 * │   │ └──┬──┘          │                      │
 * │   │  ══╧══           │  ← 일기 언더라인     │
 * │   │                  │                      │
 * │   │    ◯             │  ← 아침 (상단)       │
 * │   │  ◯ ✦ ◯          │  ← 점심(우) 취침(좌) │
 * │   │    ◯             │  ← 저녁 (하단)       │
 * │   │                  │                      │
 * │   │    ●             │  ← 진료 예약 도트    │
 * │   ╰──────────────────╯                      │
 * └─────────────────────────────────────────────┘
 */

import { useState, useEffect, useRef, type CSSProperties } from "react";
import { MOOD_COLORS, MOOD_LABELS, TIME_SLOT_LABELS, MOOD_EMOJI_MAP } from "../constants/theme";
import { getDaysInMonth, getFirstDayOfMonth, getTodayKey, toDateKey } from "../utils/date";

/* ─── 타입 ─── */
interface CalendarDayItem {
  date: string;
  moods?: Array<{ mood_level: number; time_slot?: string }>;
  has_diary?: boolean;
  hasDiary?: boolean;
}

interface CalendarProps {
  year: number;
  month: number;
  days: CalendarDayItem[];
  onSelectDate: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  selectedDate?: string;
  appointmentDates?: string[];
  /** 진료 예약 건수 맵 (date → count). 없으면 appointmentDates에서 1건으로 추론 */
  appointmentCountMap?: Record<string, number>;
  diaryDates?: string[];
}

/* ─── 헬퍼 함수 ─── */

/** 무드 레벨(1~7) → iOS 시맨틱 컬러 */
function getMoodColor(level: number): string {
  return MOOD_COLORS[level] ?? "rgba(180,180,180,0.15)";
}

/** 무드 레벨 → 라디얼 그라디언트 (중심 80% 불투명 → 가장자리 투명) */
function getMoodGradient(level: number | null): string {
  if (!level) return "radial-gradient(circle, rgba(180,180,180,0.15) 0%, rgba(180,180,180,0) 100%)";
  const color = getMoodColor(level);
  return `radial-gradient(circle, ${color}cc 0%, ${color}00 100%)`;
}

/** 날짜에 진료 예약이 있는지 확인 */
function hasAppointment(date: string, appointmentDates: string[]): boolean {
  return appointmentDates.includes(date);
}

/** 날짜에 일기가 있는지 확인 */
function hasDiary(date: string, diaryDates: string[]): boolean {
  return diaryDates.includes(date);
}

/** 진료 건수에 따른 도트 너비 */
function getAppointmentDotWidth(count: number): number {
  if (count <= 1) return 4;
  if (count === 2) return 8;
  return 12; // 3+
}

/* ─── 무드 클로버 컴포넌트 ─── */
const CLOVER_SLOTS = ["MORNING", "LUNCH", "EVENING", "BEDTIME"] as const;
const CLOVER_LABELS = ["아침 기분", "점심 기분", "저녁 기분", "취침 전 기분"];
const PETAL_COLORS: Record<string, string> = {
  MORNING: "rgba(154, 190, 240, 0.75)",
  LUNCH: "rgba(232, 185, 120, 0.75)",
  EVENING: "rgba(220, 150, 80, 0.75)",
  BEDTIME: "rgba(80, 130, 210, 0.75)",
};
// 임시 롤백 스위치: false로 바꾸면 기존 getMoodGradient 스타일로 즉시 복귀
const USE_SLOT_PETAL_COLOR = false;
// 상(아침), 우(점심), 하(저녁), 좌(취침) — 클로버 배치
const CLOVER_OFFSETS: Record<string, CSSProperties> = {
  MORNING: { top: 1.3, left: "50%", transform: "translateX(-50%)" },
  LUNCH: { top: "50%", right: 1.3, transform: "translateY(-50%)" },
  EVENING: { bottom: 1.3, left: "50%", transform: "translateX(-50%)" },
  BEDTIME: { top: "50%", left: 1.3, transform: "translateY(-50%)" },
};

function MoodClover({
  moods,
  animateIn,
}: {
  moods: { mood_level: number; time_slot: string }[];
  animateIn: boolean;
}) {
  const moodMap = new Map(moods.map((m) => [m.time_slot, m.mood_level]));
  const hasAny = moods.length > 0;
  if (!hasAny) return null;

  const petalSize = 10;
  const containerSize = petalSize + 5 * 2; // 10 + 오프셋 양쪽

  return (
    <div
      className="cal-clover"
      style={{
        position: "relative",
        width: containerSize,
        height: containerSize,
        margin: "2px auto 0",
        flexShrink: 0,
      }}
      aria-label={CLOVER_SLOTS.map((slot, i) => {
        const level = moodMap.get(slot);
        return `${CLOVER_LABELS[i]}: ${level ? MOOD_LABELS[level] : "미기록"}`;
      }).join(", ")}
    >
      {CLOVER_SLOTS.map((slot, i) => {
        const level = moodMap.get(slot) ?? null;
        return (
          <div
            key={slot}
            className="cal-clover-petal"
            style={{
              position: "absolute",
              width: petalSize,
              height: petalSize,
              borderRadius: "50%",
              background: level ? `${MOOD_COLORS[level]}BB` : "rgba(200,200,200,0.15)",
              mixBlendMode: "multiply",
              boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
              ...CLOVER_OFFSETS[slot],
              animationDelay: animateIn ? `${i * 40}ms` : "0ms",
            }}
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}

/* ─── 무드 툴팁 ─── */
function MoodTooltip({ moods }: { moods: { mood_level: number; time_slot: string }[] }) {
  const moodMap = new Map(moods.map((m) => [m.time_slot, m.mood_level]));
  return (
    <div className="cal-tooltip" role="tooltip">
      {CLOVER_SLOTS.map((slot) => {
        const level = moodMap.get(slot);
        const label = TIME_SLOT_LABELS[slot] ?? slot;
        const emoji = level ? MOOD_EMOJI_MAP[level] ?? "" : "—";
        const moodLabel = level ? MOOD_LABELS[level] : "미기록";
        return (
          <div key={slot} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, lineHeight: 1.4 }}>
            <span>{emoji}</span>
            <span style={{ fontWeight: 600 }}>{label}</span>
            <span style={{ color: "var(--cal-sub-text)" }}>{moodLabel}</span>
          </div>
        );
      })}
    </div>
  );
}

/* ─── 진료 예약 툴팁 ─── */
function AppointmentTooltip({ count }: { count: number }) {
  return (
    <div className="cal-tooltip" role="tooltip" style={{ whiteSpace: "nowrap" }}>
      <span style={{ fontSize: 11 }}>🏥 진료 예약 {count}건</span>
    </div>
  );
}

/* ─── 메인 캘린더 컴포넌트 ─── */
export function Calendar({
  year,
  month,
  days,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  selectedDate,
  appointmentDates = [],
  appointmentCountMap = {},
  diaryDates = [],
}: CalendarProps) {
  const monthIndex = month - 1;
  const daysInMonth = getDaysInMonth(year, monthIndex);
  const firstDay = getFirstDayOfMonth(year, monthIndex);
  const todayKey = getTodayKey();
  const dataMap = new Map<string, CalendarDayItem>();
  days.forEach((d) => dataMap.set(d.date, d));

  // 일기 날짜: props 또는 days 데이터에서 추출
  const diaryDateSet = new Set([
    ...diaryDates,
    ...days.filter((d) => d.has_diary || d.hasDiary).map((d) => d.date),
  ]);

  // 월 전환 애니메이션
  const [slideDir, setSlideDir] = useState<"left" | "right" | null>(null);
  const [mounted, setMounted] = useState(false);
  const prevMonthRef = useRef({ year, month });

  useEffect(() => {
    if (prevMonthRef.current.year !== year || prevMonthRef.current.month !== month) {
      const prev = prevMonthRef.current.year * 12 + prevMonthRef.current.month;
      const curr = year * 12 + month;
      setSlideDir(curr > prev ? "left" : "right");
      prevMonthRef.current = { year, month };
      const timer = setTimeout(() => setSlideDir(null), 280);
      return () => clearTimeout(timer);
    }
  }, [year, month]);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handlePrev = () => { onPrevMonth(); };
  const handleNext = () => { onNextMonth(); };

  const weekDays = ["일", "월", "화", "수", "목", "금", "토"];

  return (
    <section className="cal-container" aria-label={`${year}년 ${month}월 캘린더`}>
      {/* 헤더 */}
      <div className="cal-header">
        <button onClick={handlePrev} aria-label="이전 달" type="button" className="cal-nav-btn">‹</button>
        <strong className="cal-title">{year}년 {month}월</strong>
        <button onClick={handleNext} aria-label="다음 달" type="button" className="cal-nav-btn">›</button>
      </div>

      {/* 요일 행 */}
      <div className="cal-weekdays">
        {weekDays.map((d, i) => (
          <div
            key={d}
            className="cal-weekday"
            style={{ color: i === 0 || i === 6 ? "var(--cal-weekend)" : "var(--cal-sub-text)" }}
          >
            {d}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 */}
      <div
        className={`cal-grid ${slideDir ? `cal-slide-${slideDir}` : ""}`}
        key={`${year}-${month}`}
      >
        {/* 빈 셀 */}
        {Array(firstDay).fill(null).map((_, i) => (
          <div key={`empty-${i}`} className="cal-cell-empty" />
        ))}

        {/* 날짜 셀 */}
        {Array(daysInMonth).fill(null).map((_, i) => {
          const dayNum = i + 1;
          const dayOfWeek = (firstDay + i) % 7;
          const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
          const dateKey = toDateKey(year, monthIndex, dayNum);
          const day = dataMap.get(dateKey);
          const isSelected = selectedDate === dateKey;
          const isToday = todayKey === dateKey;
          const isAppointment = hasAppointment(dateKey, appointmentDates);
          const isDiary = diaryDateSet.has(dateKey);
          const appointmentCount = appointmentCountMap[dateKey] ?? (isAppointment ? 1 : 0);

          const dayMoods: { mood_level: number; time_slot: string }[] =
            day?.moods?.length
              ? day.moods.map((mood, idx) => ({
                  mood_level: mood.mood_level,
                  time_slot: mood.time_slot ?? ["MORNING", "LUNCH", "EVENING", "BEDTIME"][idx] ?? "MORNING",
                }))
              : [];

          return (
            <CalendarCell
              key={dateKey}
              dateKey={dateKey}
              dayNum={dayNum}
              isToday={isToday}
              isSelected={isSelected}
              isWeekend={isWeekend}
              isAppointment={isAppointment}
              isDiary={isDiary}
              appointmentCount={appointmentCount}
              moods={dayMoods}
              onSelect={onSelectDate}
              animateIn={mounted}
            />
          );
        })}
      </div>
    </section>
  );
}

/* ─── 개별 날짜 셀 ─── */
function CalendarCell({
  dateKey,
  dayNum,
  isToday,
  isSelected,
  isWeekend,
  isAppointment,
  isDiary,
  appointmentCount,
  moods,
  onSelect,
  animateIn,
}: {
  dateKey: string;
  dayNum: number;
  isToday: boolean;
  isSelected: boolean;
  isWeekend: boolean;
  isAppointment: boolean;
  isDiary: boolean;
  appointmentCount: number;
  moods: { mood_level: number; time_slot: string }[];
  onSelect: (date: string) => void;
  animateIn: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const [showMoodTip, setShowMoodTip] = useState(false);
  const [showApptTip, setShowApptTip] = useState(false);

  const cellClass = [
    "cal-cell",
    isToday ? "cal-cell--today" : "",
    isSelected ? "cal-cell--selected" : "",
  ].filter(Boolean).join(" ");

  return (
    <button
      type="button"
      className={cellClass}
      onClick={() => onSelect(dateKey)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setShowMoodTip(false); setShowApptTip(false); }}
      aria-label={`${dateKey}${isToday ? " (오늘)" : ""}${moods.length > 0 ? " 기분 기록 있음" : ""}${isAppointment ? ` 진료 예약 ${appointmentCount}건` : ""}${isDiary ? " 일기 작성됨" : ""}`}
      aria-current={isToday ? "date" : undefined}
    >
      {/* [1] 날짜 숫자 + 오늘 링 */}
      <div className="cal-cell__date-wrap">
        <span
          className={`cal-cell__date-num ${isToday ? "cal-cell__date-num--today" : ""}`}
          style={{
            color: isToday ? "var(--cal-accent)" : isWeekend ? "var(--cal-weekend)" : "var(--cal-text)",
          }}
        >
          {dayNum}
        </span>

        {/* [7] 일기 언더라인 */}
        {isDiary && (
          <div
            className={`cal-diary-bar ${hovered ? "cal-diary-bar--hover" : ""}`}
            aria-label="일기 작성됨"
          />
        )}
      </div>

      {/* [1~4] 무드 클로버 */}
      <div
        className={`cal-clover-wrap ${hovered && moods.length > 0 ? "cal-clover-wrap--hover" : ""}`}
        onMouseEnter={() => moods.length > 0 && setShowMoodTip(true)}
        onMouseLeave={() => setShowMoodTip(false)}
      >
        <MoodClover moods={moods} animateIn={animateIn} />
        {showMoodTip && moods.length > 0 && <MoodTooltip moods={moods} />}
      </div>

      {/* [6] 진료 예약 도트 */}
      {isAppointment && (
        <div
          className="cal-appt-dot-wrap"
          onMouseEnter={() => setShowApptTip(true)}
          onMouseLeave={() => setShowApptTip(false)}
        >
          <div
            className="cal-appt-dot"
            style={{ width: getAppointmentDotWidth(appointmentCount) }}
            aria-label={`진료 예약 ${appointmentCount}건`}
          />
          {showApptTip && <AppointmentTooltip count={appointmentCount} />}
        </div>
      )}
    </button>
  );
}

export default Calendar;
