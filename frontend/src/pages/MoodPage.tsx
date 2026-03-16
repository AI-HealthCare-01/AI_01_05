import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createMood, getMoods } from "../api/moods";
import { Button } from "../components/Button";
import { EmptyState } from "../components/EmptyState";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { COLORS, MOOD_COLORS } from "../constants/theme";

interface MoodItem {
  mood_id?: number;
  log_date?: string;
  time_slot?: string;
  mood_level?: number;
}

export function MoodPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<MoodItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logDate, setLogDate] = useState("");
  const [timeSlot, setTimeSlot] = useState("MORNING");
  const [moodLevel, setMoodLevel] = useState(4);

  const fetchMoods = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result: unknown = await getMoods();
      if (Array.isArray(result)) {
        setItems(result as MoodItem[]);
      } else if (result && typeof result === "object" && "data" in result && Array.isArray((result as { data: unknown }).data)) {
        setItems((result as { data: MoodItem[] }).data);
      } else {
        setItems([]);
      }
    } catch {
      setError("기분 기록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchMoods();
  }, []);

  const submit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      await createMood({ log_date: logDate, time_slot: timeSlot, mood_level: moodLevel });
      await fetchMoods();
    } catch {
      setError("기분 기록 저장에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 460, display: "grid", gap: 12, alignContent: "start" }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "15px",
          color: COLORS.subText,
          fontWeight: 600,
          padding: "16px 0",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
      </button>
      <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>기분 기록</h1>
      <section style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff", display: "grid", gap: 8 }}>
        <input type="date" value={logDate} onChange={(event) => setLogDate(event.target.value)} />
        <select value={timeSlot} onChange={(event) => setTimeSlot(event.target.value)}>
          <option value="MORNING">MORNING</option>
          <option value="LUNCH">LUNCH</option>
          <option value="EVENING">EVENING</option>
          <option value="BEDTIME">BEDTIME</option>
        </select>
        <select value={moodLevel} onChange={(event) => setMoodLevel(Number(event.target.value))}>
          {[1, 2, 3, 4, 5, 6, 7].map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
        <Button type="button" onClick={() => void submit()} loading={isSubmitting}>
          저장
        </Button>
      </section>
      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchMoods()} /> : null}
      {!isLoading && !error && items.length === 0 ? <EmptyState message="기분 기록이 없습니다." /> : null}
      {!isLoading && !error && items.length > 0 ? (
        <section style={{ display: "grid", gap: 8 }}>
          {items.map((item, index) => (
            <article key={`${item.mood_id ?? "mood"}-${index}`} style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff" }}>
              <p style={{ margin: 0 }}>{item.log_date}</p>
              <p style={{ margin: "4px 0 0", color: COLORS.placeholder }}>{item.time_slot}</p>
              <span
                style={{
                  display: "inline-block",
                  marginTop: 8,
                  width: 12,
                  height: 12,
                  borderRadius: 999,
                  backgroundColor: item.mood_level ? MOOD_COLORS[item.mood_level] : "#bbb",
                }}
              />
            </article>
          ))}
        </section>
      ) : null}
      </div>
    </main>
  );
}
