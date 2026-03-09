import { COLORS, MOOD_COLORS } from "../constants/theme";
import { getDaysInMonth, getFirstDayOfMonth, getTodayKey, toDateKey } from "../utils/date";

interface CalendarDayItem {
  date: string;
  moods?: Array<{ mood_level: number; time_slot?: string }>;
}

interface CalendarProps {
  year: number;
  month: number;
  days: CalendarDayItem[];
  onSelectDate: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  selectedDate?: string;
}

const MoodFlower = ({ moods }: { moods: { mood_level: number; time_slot: string }[] }) => {
  const getColor = (slot: string) => {
    const mood = moods.find((m) => m.time_slot === slot);
    return mood ? MOOD_COLORS[mood.mood_level] : COLORS.border;
  };

  const hasAny = moods.length > 0;
  if (!hasAny) return null;

  return (
    <div
      style={{
        position: "relative",
        width: "22px",
        height: "22px",
        marginTop: "2px",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "13px",
          height: "13px",
          borderRadius: "50%",
          background: getColor("MORNING"),
          border: `1.5px solid ${COLORS.buttonText}`,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 0,
          width: "13px",
          height: "13px",
          borderRadius: "50%",
          background: getColor("LUNCH"),
          border: `1.5px solid ${COLORS.buttonText}`,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "13px",
          height: "13px",
          borderRadius: "50%",
          background: getColor("EVENING"),
          border: `1.5px solid ${COLORS.buttonText}`,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: "13px",
          height: "13px",
          borderRadius: "50%",
          background: getColor("BEDTIME"),
          border: `1.5px solid ${COLORS.buttonText}`,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: "8px",
          color: COLORS.cardBg,
          fontWeight: 900,
          zIndex: 1,
          lineHeight: 1,
          textShadow: "0 0 2px rgba(0,0,0,0.3)",
        }}
      >
        ✓
      </div>
    </div>
  );
};

export function Calendar({
  year,
  month,
  days,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  selectedDate,
}: CalendarProps) {
  const monthIndex = month - 1;
  const daysInMonth = getDaysInMonth(year, monthIndex);
  const firstDay = getFirstDayOfMonth(year, monthIndex);
  const todayKey = getTodayKey();
  const dataMap = new Map<string, CalendarDayItem>();
  days.forEach((d) => dataMap.set(d.date, d));

  return (
    <section style={{ display: "grid", gap: 12, background: COLORS.cardBg, border: `1px solid ${COLORS.border}`, borderRadius: 16 }}>
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", padding: "16px 20px", borderBottom: `1px solid ${COLORS.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            onClick={onPrevMonth}
            aria-label="이전 달"
            type="button"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, lineHeight: 1, padding: 0 }}
          >
            ‹
          </button>
          <strong>
            {year}년 {month}월
          </strong>
          <button
            onClick={onNextMonth}
            aria-label="다음 달"
            type="button"
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 20, lineHeight: 1, padding: 0 }}
          >
            ›
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 8, padding: "10px 8px 12px" }}>
        {Array(firstDay)
          .fill(null)
          .map((_, i) => (
            <div key={`empty-${i}`} />
          ))}
        {Array(daysInMonth)
          .fill(null)
          .map((_, i) => {
            const dayNum = i + 1;
            const dateKey = toDateKey(year, monthIndex, dayNum);
            const day = dataMap.get(dateKey);
            const isSelected = selectedDate === dateKey;
            const isToday = todayKey === dateKey;
            const dayMoods: { mood_level: number; time_slot: string }[] =
              day?.moods && day.moods.length > 0
                ? day.moods.map((mood, idx) => ({
                    mood_level: mood.mood_level,
                    time_slot: mood.time_slot ?? ["MORNING", "LUNCH", "EVENING", "BEDTIME"][idx] ?? "MORNING",
                  }))
                : [];

            return (
              <button
                key={dateKey}
                type="button"
                onClick={() => onSelectDate(dateKey)}
                style={{
                  minHeight: 56,
                  borderRadius: 8,
                  border: isSelected ? `1px solid ${COLORS.buttonBg}` : "1px solid transparent",
                  background: isSelected ? COLORS.selectedCellBg : COLORS.cardBg,
                  display: "grid",
                  placeItems: "center",
                  position: "relative",
                }}
              >
                <span
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: 999,
                    display: "grid",
                    placeItems: "center",
                    background: isToday ? COLORS.buttonBg : "transparent",
                    color: isToday ? COLORS.buttonText : COLORS.text,
                  }}
                >
                  {dayNum}
                </span>
                {dayMoods.length > 0 ? <MoodFlower moods={dayMoods} /> : null}
              </button>
            );
          })}
      </div>
    </section>
  );
}
