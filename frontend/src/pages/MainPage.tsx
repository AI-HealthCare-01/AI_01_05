import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";

import {
  getHomeAppointmentNext,
  getHomeMedicationsToday,
  getHomeMoodsToday,
  patchHomeMedicationCheck,
  postHomeMoodToday,
  type HomeMedicationItem,
} from "../api/home";
import chamkkaeImage from "../assets/images/chatbots/chamkkae-removebg.png";

type UiSlot = "morning" | "lunch" | "dinner" | "night";
type ApiSlot = "MORNING" | "LUNCH" | "EVENING" | "BEDTIME";

type MoodBySlot = Record<UiSlot, number | null>;

type MedicationUiItem = {
  id: number;
  medicationId: number;
  name: string;
  dosage: number;
  timeSlot: UiSlot;
  checked: boolean;
};

const TIME_SLOTS: Array<{ key: UiSlot; label: string }> = [
  { key: "morning", label: "아침" },
  { key: "lunch", label: "점심" },
  { key: "dinner", label: "저녁" },
  { key: "night", label: "취침 전" },
];

const MOOD_EMOJI: Record<number, string> = {
  1: "😡",
  2: "😢",
  3: "😟",
  4: "😐",
  5: "🙂",
  6: "😊",
  7: "😄",
};

const MOOD_COLORS: Record<number, string> = {
  1: "#e73a35",
  2: "#ec6a3b",
  3: "#f19a4a",
  4: "#f2c66a",
  5: "#90bde3",
  6: "#5b8fcc",
  7: "#2e67b1",
};

const MOOD_MESSAGES: Record<string, string> = {
  1: "오늘 많이 힘드셨군요. 푹 쉬어요 🥺",
  2: "마음이 무거운 하루였나요? 내일은 더 나아질 거예요.",
  3: "조금 지쳤나요? 오늘 하루도 수고했어요.",
  4: "오늘은 마음을 내려놓고 하루를 즐겨보아요 😊",
  5: "기분이 괜찮은 하루네요! 좋은 하루 보내요.",
  6: "오늘 기분이 좋군요! 그 기운 유지해요 😄",
  7: "오늘 기분 최고네요! 신나는 하루 보내요 🎉",
  default: "오늘 기분은 어때요? 😊",
};

const cardStyle: CSSProperties = {
  background: "#FFFFFF",
  borderRadius: "20px",
  border: "1px solid #E0E0E0",
  padding: "20px",
  marginBottom: "20px",
};

const topButtonStyle: CSSProperties = {
  background: "#99A988",
  color: "#FFFFFF",
  border: "none",
  borderRadius: "12px",
  padding: "10px 14px",
  fontWeight: 700,
  cursor: "pointer",
};

const swipeContainerStyle: CSSProperties = {
  display: "flex",
  overflowX: "auto",
  scrollSnapType: "x mandatory",
  WebkitOverflowScrolling: "touch",
  gap: "16px",
  scrollbarWidth: "none",
  msOverflowStyle: "none",
};

const swipePageStyle: CSSProperties = {
  minWidth: "100%",
  scrollSnapAlign: "start",
};

const stampStyle: CSSProperties = {
  position: "absolute",
  top: "10px",
  right: "10px",
  background: "rgba(0,0,0,0.6)",
  color: "#fff",
  padding: "6px 12px",
  borderRadius: "10px",
  fontSize: "12px",
};

const emojiButtonBaseStyle: CSSProperties = {
  width: "48px",
  height: "48px",
  borderRadius: "50%",
  border: "1px solid #ddd",
  background: "#fff",
  fontSize: "20px",
  cursor: "pointer",
};

function uiToApiSlot(uiSlot: UiSlot): ApiSlot {
  if (uiSlot === "morning") return "MORNING";
  if (uiSlot === "lunch") return "LUNCH";
  if (uiSlot === "dinner") return "EVENING";
  return "BEDTIME";
}

function apiToUiSlot(apiSlot: string): UiSlot {
  if (apiSlot === "MORNING" || apiSlot === "morning") return "morning";
  if (apiSlot === "LUNCH" || apiSlot === "lunch") return "lunch";
  if (apiSlot === "EVENING" || apiSlot === "DINNER" || apiSlot === "dinner") return "dinner";
  return "night";
}

function getEmojiButtonStyle(level: number, selected: boolean): CSSProperties {
  return {
    ...emojiButtonBaseStyle,
    background: selected ? MOOD_COLORS[level] : `${MOOD_COLORS[level]}22`,
    transform: selected ? "scale(1.2)" : "scale(1)",
    boxShadow: selected ? "0 4px 10px rgba(0,0,0,0.15)" : "none",
    transition: "all 0.15s ease",
  };
}

function getCurrentUiSlot(): UiSlot {
  const hour = new Date().getHours();
  if (hour < 11) return "morning";
  if (hour < 15) return "lunch";
  if (hour < 21) return "dinner";
  return "night";
}

export default function MainPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [hasUpcoming, setHasUpcoming] = useState(false);
  const [dDay, setDDay] = useState<number | null>(null);

  const [todayMoods, setTodayMoods] = useState<MoodBySlot>({
    morning: null,
    lunch: null,
    dinner: null,
    night: null,
  });
  const [latestMood, setLatestMood] = useState<number | null>(null);
  const [isSavingMood, setIsSavingMood] = useState(false);

  const [todayMedications, setTodayMedications] = useState<MedicationUiItem[]>([]);
  const [isSavingMedication, setIsSavingMedication] = useState(false);



  const initialSlot = getCurrentUiSlot();
  const initialIndex = TIME_SLOTS.findIndex((slot) => slot.key === initialSlot);
  const [moodSwipeIndex, setMoodSwipeIndex] = useState(initialIndex < 0 ? 0 : initialIndex);
  const [medSwipeIndex, setMedSwipeIndex] = useState(initialIndex < 0 ? 0 : initialIndex);

  const moodSwipeRef = useRef<HTMLDivElement | null>(null);
  const medSwipeRef = useRef<HTMLDivElement | null>(null);

  const fetchTodayMoods = async () => {
    const res = await getHomeMoodsToday();

    const nextMoods: MoodBySlot = {
      morning: null,
      lunch: null,
      dinner: null,
      night: null,
    };

    const list = res?.moods ?? [];
    list.forEach((item) => {
      const uiSlot = apiToUiSlot(item.timeSlot);
      nextMoods[uiSlot] = item.moodLevel;
    });

    setTodayMoods(nextMoods);

    if (list.length > 0) {
      const latest = [...list].sort(
        (a, b) => new Date(b.recordedAt).getTime() - new Date(a.recordedAt).getTime()
      )[0];
      setLatestMood(latest.moodLevel);
    } else {
      setLatestMood(null);
    }
  };

  const fetchTodayMedications = async () => {
    const res = await getHomeMedicationsToday();
    const mapped: MedicationUiItem[] = (res?.items ?? []).map((item: HomeMedicationItem) => ({
      id: item.medicationId,
      medicationId: item.medicationId,
      name: item.name,
      dosage: item.dosePerIntake,
      timeSlot: apiToUiSlot(item.timeSlot),
      checked: item.isTaken,
    }));
    setTodayMedications(mapped);
  };

  const fetchHome = async () => {
    setError("");
    setLoading(true);

    try {
      const appointment = await getHomeAppointmentNext();
      setHasUpcoming(Boolean(appointment?.hasUpcoming));
      setDDay(appointment?.dDay ?? null);

      await Promise.all([fetchTodayMoods(), fetchTodayMedications()]);
    } catch (fetchError) {
      const message = fetchError instanceof Error ? fetchError.message : "홈 데이터를 불러오지 못했습니다.";
      setError(message);
      setHasUpcoming(false);
      setDDay(null);
      setTodayMoods({ morning: null, lunch: null, dinner: null, night: null });
      setLatestMood(null);
      setTodayMedications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHome();
  }, []);

  useEffect(() => {
    const index = initialIndex < 0 ? 0 : initialIndex;
    scrollMoodToIndex(index);
    scrollMedToIndex(index);
  }, []);

  const handleMoodClick = async (slot: UiSlot, level: number) => {
    const previousLevel = todayMoods[slot];
    setTodayMoods((prev) => ({
      ...prev,
      [slot]: level,
    }));
    setLatestMood(level);

    try {
      setIsSavingMood(true);
      setError("");

      try {
        await postHomeMoodToday({
          timeSlot: slot,
          moodLevel: level,
        });
      } catch {
        await postHomeMoodToday({
          timeSlot: uiToApiSlot(slot),
          moodLevel: level,
        });
      }

      await fetchTodayMoods();
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "기분 저장에 실패했습니다.";
      if (message.includes("MOOD_ALREADY_RECORDED") || message.includes("409")) {
        setError("이미 기록된 시간대라 서버에는 반영되지 않았지만, 화면 선택은 유지합니다.");
      } else {
        setTodayMoods((prev) => ({
          ...prev,
          [slot]: previousLevel ?? null,
        }));
        setLatestMood(previousLevel ?? null);
        setError(message);
      }
      console.error(saveError);
    } finally {
      setIsSavingMood(false);
    }
  };

  const handleMedicationToggle = async (medicationId: number, checked: boolean) => {
    try {
      setIsSavingMedication(true);
      setError("");
      await patchHomeMedicationCheck(medicationId, !checked);
      await fetchTodayMedications();
    } catch (patchError) {
      const message = patchError instanceof Error ? patchError.message : "복약 상태 변경에 실패했습니다.";
      setError(message);
    } finally {
      setIsSavingMedication(false);
    }
  };

  const dDayText = hasUpcoming && dDay !== null ? `D-${dDay}` : "진료 없음";

  const characterMessage = latestMood
    ? MOOD_MESSAGES[String(latestMood)] ?? MOOD_MESSAGES.default
    : MOOD_MESSAGES.default;

  const medsBySlot = useMemo(() => {
    return {
      morning: todayMedications.filter((med) => med.timeSlot === "morning"),
      lunch: todayMedications.filter((med) => med.timeSlot === "lunch"),
      dinner: todayMedications.filter((med) => med.timeSlot === "dinner"),
      night: todayMedications.filter((med) => med.timeSlot === "night"),
    };
  }, [todayMedications]);

  const totalCount = todayMedications.length;
  const completeCount = todayMedications.filter((med) => med.checked).length;

  const updateMoodIndicator = () => {
    if (!moodSwipeRef.current) return;
    const container = moodSwipeRef.current;
    const page = container.clientWidth + 16;
    const index = Math.round(container.scrollLeft / page);
    setMoodSwipeIndex(Math.max(0, Math.min(TIME_SLOTS.length - 1, index)));
  };

  const updateMedIndicator = () => {
    if (!medSwipeRef.current) return;
    const container = medSwipeRef.current;
    const page = container.clientWidth + 16;
    const index = Math.round(container.scrollLeft / page);
    setMedSwipeIndex(Math.max(0, Math.min(TIME_SLOTS.length - 1, index)));
  };

  const scrollMoodToIndex = (index: number) => {
    if (!moodSwipeRef.current) return;
    const container = moodSwipeRef.current;
    const firstPage = container.firstElementChild as HTMLElement | null;
    const pageWidth = (firstPage?.clientWidth ?? container.clientWidth) + 16;
    container.scrollTo({ left: pageWidth * index, behavior: "smooth" });
    setMoodSwipeIndex(index);
  };

  const scrollMedToIndex = (index: number) => {
    if (!medSwipeRef.current) return;
    const container = medSwipeRef.current;
    const firstPage = container.firstElementChild as HTMLElement | null;
    const pageWidth = (firstPage?.clientWidth ?? container.clientWidth) + 16;
    container.scrollTo({ left: pageWidth * index, behavior: "smooth" });
    setMedSwipeIndex(index);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#F5F5F5",
        color: "#2C2C2C",
        padding: "16px",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <style>{`
        .swipeContainer::-webkit-scrollbar {
          display: none;
        }
      `}</style>

      <div style={{ width: "100%", maxWidth: 460 }}>
        <div style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button style={topButtonStyle} onClick={() => navigate("/diary")}>일기</button>
          <div style={{ color: "#99A988", fontWeight: 800, fontSize: 18 }}>{dDayText}</div>
          <button style={topButtonStyle} onClick={() => navigate("/mypage")}>내 정보</button>
        </div>

        <div style={{ ...cardStyle, textAlign: "center" }}>
          <img
            src={chamkkaeImage}
            alt="기본 캐릭터"
            style={{ width: 180, maxWidth: "70%", objectFit: "contain", marginBottom: 8, cursor: "pointer" }}
            onClick={() => navigate("/chat")}
          />
          <p style={{ margin: 0, fontWeight: 600, lineHeight: 1.6 }}>{characterMessage}</p>
        </div>

        <div style={cardStyle}>
          <h2 style={{ margin: "0 0 12px" }}>오늘의 기분</h2>

          <div
            ref={moodSwipeRef}
            className="swipeContainer"
            style={swipeContainerStyle}
            onScroll={updateMoodIndicator}
          >
            {TIME_SLOTS.map((slot) => (
              <div key={slot.key} style={swipePageStyle}>
                <h3 style={{ margin: "0 0 10px", fontSize: 15, lineHeight: 1.4, paddingTop: 2 }}>오늘의 {slot.label} 기분</h3>

                <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                  {Object.entries(MOOD_EMOJI).map(([level, emoji]) => {
                    const numeric = Number(level);
                    const selected = todayMoods[slot.key] === numeric;
                    return (
                      <button
                        key={`${slot.key}-${level}`}
                        onClick={() => handleMoodClick(slot.key, numeric)}
                        disabled={loading || isSavingMood}
                        style={getEmojiButtonStyle(numeric, selected)}
                      >
                        {emoji}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 10 }}>
            {TIME_SLOTS.map((slot, index) => (
              <div
                key={`mood-dot-${slot.key}`}
                onClick={() => scrollMoodToIndex(index)}
                style={{
                  width: index === moodSwipeIndex ? 16 : 8,
                  height: 8,
                  borderRadius: 999,
                  background: index === moodSwipeIndex ? "#99A988" : "#DADADA",
                  transition: "all 0.2s ease",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>

          {TIME_SLOTS.every((slot) => todayMoods[slot.key] === null) && (
            <div style={{ marginTop: 10, fontSize: 14, color: "#757575" }}>아직 기록된 기분이 없어요.</div>
          )}
        </div>

        <div style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>오늘의 복약</h2>
            <button style={topButtonStyle} onClick={() => navigate('/medications/add')}>약 추가</button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <div style={{ minWidth: 74, fontSize: 13, color: "#757575" }}>
              {completeCount} / {totalCount}
            </div>
            <div style={{ flex: 1, height: 8, borderRadius: 999, background: "#E8E8E8", overflow: "hidden" }}>
              <div
                style={{
                  width: totalCount === 0 ? "0%" : `${(completeCount / totalCount) * 100}%`,
                  height: "100%",
                  background: "#99A988",
                }}
              />
            </div>
          </div>

          <div
            ref={medSwipeRef}
            className="swipeContainer"
            style={swipeContainerStyle}
            onScroll={updateMedIndicator}
          >
            {TIME_SLOTS.map((slot) => {
              const medications = medsBySlot[slot.key];
              const completed = medications.filter((med) => med.checked).length;
              const total = medications.length;
              const allDone = total > 0 && completed === total;

              return (
                <div
                  key={slot.key}
                  style={{
                    ...swipePageStyle,
                    position: "relative",
                    opacity: allDone ? 0.5 : 1,
                    filter: allDone ? "grayscale(40%)" : "none",
                  }}
                >
                  <h3 style={{ margin: "0 0 10px", fontSize: 15 }}>오늘의 {slot.label} 약</h3>

                  {allDone && <div style={stampStyle}>✔ 복용 완료</div>}

                  {medications.map((med) => (
                    <div
                      key={med.id}
                      onClick={() => handleMedicationToggle(med.medicationId, med.checked)}
                      style={{
                        padding: "8px",
                        marginBottom: "6px",
                        borderRadius: "8px",
                        border: "1px solid #E0E0E0",
                        background: med.checked ? "#F0F5F0" : "#FFFFFF",
                        textDecoration: med.checked ? "line-through" : "none",
                        cursor: "pointer",
                      }}
                    >
                      {med.checked ? "☑" : "☐"} {med.name} {med.dosage}정
                    </div>
                  ))}

                  {medications.length === 0 && (
                    <div style={{ fontSize: 14, color: "#757575" }}>등록된 약이 없습니다.</div>
                  )}
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 10 }}>
            {TIME_SLOTS.map((slot, index) => (
              <div
                key={`med-dot-${slot.key}`}
                onClick={() => scrollMedToIndex(index)}
                style={{
                  width: index === medSwipeIndex ? 16 : 8,
                  height: 8,
                  borderRadius: 999,
                  background: index === medSwipeIndex ? "#99A988" : "#DADADA",
                  transition: "all 0.2s ease",
                  cursor: "pointer",
                }}
              />
            ))}
          </div>

          {totalCount === 0 && (
            <div style={{ marginTop: 10, fontSize: 14, color: "#757575" }}>오늘 등록된 복약 항목이 없어요.</div>
          )}

          {totalCount > 0 && completeCount === totalCount && (
            <div
              style={{
                marginTop: 12,
                borderRadius: 12,
                background: "#F0F5F0",
                color: "#99A988",
                fontWeight: 800,
                padding: "10px 12px",
                textAlign: "center",
              }}
            >
              🎉 오늘 복약을 모두 완료했어요!
            </div>
          )}
        </div>

        {loading && <div style={cardStyle}>데이터를 불러오는 중입니다...</div>}

        {error && (
          <div style={{ ...cardStyle, border: "1px solid #FF0000", color: "#FF0000" }}>
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
