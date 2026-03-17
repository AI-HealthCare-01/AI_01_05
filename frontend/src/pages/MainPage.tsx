import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";

import {
  getHomeMedicationsToday,
  getHomeMoodsToday,
  patchHomeMedicationCheck,
  postHomeMoodToday,
  type HomeMedicationItem,
} from "../api/home";
import { getNextAppointment } from "../api/appointments";
import { getMedicineDetail, type MedicineDetailItem } from "../api/medicines";
import { getMyCharacter } from "../apis/characterApi";
import { CHARACTER_IMAGE_BY_ID, DEFAULT_CHARACTER_IMAGE } from "../constants/characters";
import { COLORS } from "../constants/theme";
import { useAuthStore } from "../store/authStore";

type UiSlot = "morning" | "lunch" | "dinner" | "night";
type ApiSlot = "MORNING" | "LUNCH" | "EVENING" | "BEDTIME";

type MoodBySlot = Record<UiSlot, number | null>;

type MedicationUiItem = {
  id: number;
  medicationId: number;
  itemSeq: string;
  name: string;
  dosage: number;
  timeSlot: UiSlot;
  checked: boolean;
  itemImage: string | null;
};

type NextAppointmentUi = {
  dDay: string;
  hospitalName: string | null;
  dateLabel: string;
  timeLabel: string | null;
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

const GREETING_MESSAGES = [
  "오늘 기분은 어때요? 😊",
  "밥은 먹었어요? 🍚",
  "오늘 산책 나가는 건 어때요? 🐾",
  "물 충분히 마셨어요? 💧",
  "잠은 잘 잤어요? 😴",
  "오늘도 함께해서 좋아요 🐶",
  "오늘 하루도 잘 부탁해요! 🌿",
];

const COMPLETION_MESSAGES: Record<UiSlot, string> = {
  morning: "아침 약을 다 드셨네요! 대단해요! 💊",
  lunch: "점심 약을 다 드셨네요! 대단해요! 💊",
  dinner: "저녁 약을 다 드셨네요! 잘하고 있어요! 💊",
  night: "오늘 하루 약을 모두 챙겼어요! 최고예요 🐾",
};

const MOOD_MESSAGES: Record<string, string> = {
  1: "오늘 많이 힘드셨군요. 푹 쉬어요 🥺",
  2: "마음이 무거운 하루였나요? 내일은 더 나아질 거예요.",
  3: "조금 지쳤나요? 오늘 하루도 수고했어요.",
  4: "오늘은 마음을 내려놓고 하루를 즐겨보아요 😊",
  5: "기분이 괜찮은 하루네요! 좋은 하루 보내요.",
  6: "오늘 기분이 좋군요! 그 기운 유지해요 😄",
  7: "오늘 기분 최고네요! 신나는 하루 보내요 🎉",
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
  borderRadius: "14px",
  padding: "10px 18px",
  fontWeight: 700,
  fontSize: 14,
  boxShadow: "0 4px 12px rgba(153,169,136,0.35)",
  cursor: "pointer",
};

const swipeContainerStyle: CSSProperties = {
  display: "flex",
  overflow: "hidden",
  overflowY: "hidden",
  scrollSnapType: "x mandatory",
  WebkitOverflowScrolling: "touch",
  gap: "0px",
  paddingLeft: "0px",
  paddingRight: "0px",
  scrollbarWidth: "none",
  msOverflowStyle: "none",
};

const swipePageStyle: CSSProperties = {
  flex: "0 0 100%",
  width: "100%",
  scrollSnapAlign: "start",
};

const pawStampStyle: CSSProperties = {
  position: "absolute",
  top: "50%",
  left: "50%",
  transform: "translate(-50%, -50%) rotate(-15deg)",
  fontSize: 160,
  opacity: 0.35,
  zIndex: 5,
  pointerEvents: "none",
  userSelect: "none",
};

const emojiButtonBaseStyle: CSSProperties = {
  width: "36px",
  height: "36px",
  borderRadius: "50%",
  border: "1px solid #ddd",
  background: "#fff",
  fontSize: "16px",
  cursor: "pointer",
};

const EMOJI_ANIMATIONS: Record<number, string> = {
  1: "mood-shake 0.5s ease-in-out 1",
  2: "mood-sob 1.2s ease-in-out 1",
  3: "mood-worry 1.5s ease-in-out 1",
  4: "mood-neutral 2s ease-in-out 1",
  5: "mood-bounce 1s ease-in-out 1",
  6: "mood-happy 0.8s ease-in-out 1",
  7: "mood-spin 1s ease-in-out 1",
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
    border: selected ? "3px solid #99A988" : "2px solid transparent",
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

function toDateLabel(appointmentDate: string): string {
  const [year, month, day] = appointmentDate.split("-").map(Number);
  if (!year || !month || !day) return "진료 일정";
  return `${month}월 ${day}일`;
}

function toTimeLabel(appointmentTime: string | null): string | null {
  if (!appointmentTime) return null;
  const [hourText, minuteText] = appointmentTime.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null;
  const period = hour < 12 ? "오전" : "오후";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${period} ${displayHour}:${String(minute).padStart(2, "0")}`;
}

function toDdayLabel(appointmentDate: string): string {
  const [year, month, day] = appointmentDate.split("-").map(Number);
  if (!year || !month || !day) return "D-day";
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const target = new Date(year, month - 1, day);
  const diffDays = Math.floor((target.getTime() - startOfToday.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "D-day";
  return `D-${diffDays}`;
}

// ── 스켈레톤 컴포넌트 ──
function SkeletonBlock({ width = "100%", height = 20, style }: { width?: string | number; height?: number; style?: CSSProperties }) {
  return <div className="skeleton" style={{ width, height, ...style }} />;
}

function MainPageSkeleton() {
  return (
    <div style={{ width: "100%", maxWidth: 460 }}>
      {/* 헤더 카드 */}
      <div style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <SkeletonBlock width={72} height={38} style={{ borderRadius: 14 }} />
        <SkeletonBlock width={100} height={48} style={{ borderRadius: 12 }} />
        <SkeletonBlock width={72} height={38} style={{ borderRadius: 14 }} />
      </div>
      {/* 캐릭터 카드 */}
      <div style={{ ...cardStyle, display: "flex", flexDirection: "column", alignItems: "center", gap: 16, paddingTop: 32, paddingBottom: 32 }}>
        <SkeletonBlock width="80%" height={24} style={{ borderRadius: 12 }} />
        <SkeletonBlock width={180} height={180} style={{ borderRadius: 16 }} />
        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
          {Array.from({ length: 7 }).map((_, i) => (
            <SkeletonBlock key={i} width={36} height={36} style={{ borderRadius: "50%" }} />
          ))}
        </div>
      </div>
      {/* 복약 카드 */}
      <div style={{ ...cardStyle }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <SkeletonBlock width={100} height={20} />
          <SkeletonBlock width={72} height={36} style={{ borderRadius: 14 }} />
        </div>
        <SkeletonBlock width="100%" height={8} style={{ borderRadius: 999, marginBottom: 12 }} />
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonBlock key={i} width="100%" height={44} style={{ borderRadius: 8, marginBottom: 8 }} />
        ))}
      </div>
    </div>
  );
}

export default function MainPage() {
  const navigate = useNavigate();
  const [pageLeaving, setPageLeaving] = useState(false);

  const navigateWithFade = useCallback((to: string) => {
    setPageLeaving(true);
    setTimeout(() => navigate(to), 200);
  }, [navigate]);
  const selectedCharacter = useAuthStore((s) => s.selectedCharacter);
  const setSelectedCharacter = useAuthStore((s) => s.setSelectedCharacter);
  const [characterImage, setCharacterImage] = useState(DEFAULT_CHARACTER_IMAGE);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [nextAppointment, setNextAppointment] = useState<NextAppointmentUi | null>(null);

  const [todayMoods, setTodayMoods] = useState<MoodBySlot>({
    morning: null,
    lunch: null,
    dinner: null,
    night: null,
  });
  const [latestMood, setLatestMood] = useState<number | null>(null);
  const [greetingMessage] = useState(() => {
    const idx = Math.floor(Math.random() * GREETING_MESSAGES.length);
    return GREETING_MESSAGES[idx];
  });
  const [isSavingMood, setIsSavingMood] = useState(false);
  const [animatedEmoji, setAnimatedEmoji] = useState<{ slot: UiSlot; level: number; nonce: number } | null>(null);

  const [todayMedications, setTodayMedications] = useState<MedicationUiItem[]>([]);
  const [isSavingMedication, setIsSavingMedication] = useState(false);
  const [pawStampTokenBySlot, setPawStampTokenBySlot] = useState<Record<UiSlot, number>>({
    morning: 0,
    lunch: 0,
    dinner: 0,
    night: 0,
  });
  const [expandedMedicationId, setExpandedMedicationId] = useState<number | null>(null);
  const [detailByMedicationId, setDetailByMedicationId] = useState<Record<number, MedicineDetailItem | null>>({});
  const [loadingDetailByMedicationId, setLoadingDetailByMedicationId] = useState<Record<number, boolean>>({});
  const [detailErrorByMedicationId, setDetailErrorByMedicationId] = useState<Record<number, string>>({});

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
      itemSeq: item.itemSeq,
      name: item.name,
      dosage: item.dosePerIntake,
      timeSlot: apiToUiSlot(item.timeSlot),
      checked: item.isTaken,
      itemImage: item.itemImage,
    }));
    setTodayMedications(mapped);
  };

  const fetchHome = async () => {
    setError("");
    setLoading(true);

    try {
      const appointment = await getNextAppointment();
      if (appointment && appointment.appointment_date) {
        setNextAppointment({
          dDay: toDdayLabel(appointment.appointment_date),
          hospitalName: appointment.hospital_name ?? null,
          dateLabel: toDateLabel(appointment.appointment_date),
          timeLabel: toTimeLabel(appointment.appointment_time),
        });
      } else {
        setNextAppointment(null);
      }

      await Promise.all([fetchTodayMoods(), fetchTodayMedications()]);
    } catch (fetchError) {
      const message = fetchError instanceof Error ? fetchError.message : "홈 데이터를 불러오지 못했습니다.";
      setError(message);
      setNextAppointment(null);
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
    if (!selectedCharacter?.id) return;
    setCharacterImage(CHARACTER_IMAGE_BY_ID[selectedCharacter.id] ?? DEFAULT_CHARACTER_IMAGE);
  }, [selectedCharacter]);

  useEffect(() => {
    getMyCharacter()
      .then((data) => {
        const nextImage = CHARACTER_IMAGE_BY_ID[data.character_id] ?? DEFAULT_CHARACTER_IMAGE;
        setCharacterImage(nextImage);
        setSelectedCharacter({
          id: data.character_id,
          name: data.name,
          imageUrl: nextImage,
        });
      })
      .catch(() => {
        setCharacterImage(DEFAULT_CHARACTER_IMAGE);
      });
  }, [setSelectedCharacter]);

  useEffect(() => {
    const index = initialIndex < 0 ? 0 : initialIndex;
    scrollMoodToIndex(index);
    scrollMedToIndex(index);
  }, []);

  const handleMoodClick = async (slot: UiSlot, level: number) => {
    setAnimatedEmoji({ slot, level, nonce: Date.now() });
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

  const handleMedicationToggle = async (medicationId: number, checked: boolean, timeSlot: UiSlot) => {
    try {
      setIsSavingMedication(true);
      setError("");
      await patchHomeMedicationCheck(medicationId, !checked, uiToApiSlot(timeSlot));
      await fetchTodayMedications();
    } catch (patchError) {
      const message = patchError instanceof Error ? patchError.message : "복약 상태 변경에 실패했습니다.";
      setError(message);
    } finally {
      setIsSavingMedication(false);
    }
  };

  const handleMedicationDetailToggle = async (med: MedicationUiItem) => {
    if (expandedMedicationId === med.medicationId) {
      setExpandedMedicationId(null);
      return;
    }

    setExpandedMedicationId(med.medicationId);

    const hasLoaded = Object.prototype.hasOwnProperty.call(detailByMedicationId, med.medicationId);
    if (hasLoaded) return;

    setLoadingDetailByMedicationId((prev) => ({ ...prev, [med.medicationId]: true }));
    setDetailErrorByMedicationId((prev) => ({ ...prev, [med.medicationId]: "" }));
    try {
      const detail = await getMedicineDetail(med.itemSeq);
      setDetailByMedicationId((prev) => ({ ...prev, [med.medicationId]: detail }));
    } catch {
      setDetailErrorByMedicationId((prev) => ({
        ...prev,
        [med.medicationId]: "약 상세 정보를 불러오지 못했습니다.",
      }));
    } finally {
      setLoadingDetailByMedicationId((prev) => ({ ...prev, [med.medicationId]: false }));
    }
  };

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
  const lastActiveSlot = useMemo(
    () => [...TIME_SLOTS].reverse().find((slot) => medsBySlot[slot.key].length > 0)?.key ?? null,
    [medsBySlot]
  );
  const allDoneBySlot = useMemo<Record<UiSlot, boolean>>(
    () => ({
      morning: medsBySlot.morning.length > 0 && medsBySlot.morning.every((med) => med.checked),
      lunch: medsBySlot.lunch.length > 0 && medsBySlot.lunch.every((med) => med.checked),
      dinner: medsBySlot.dinner.length > 0 && medsBySlot.dinner.every((med) => med.checked),
      night: medsBySlot.night.length > 0 && medsBySlot.night.every((med) => med.checked),
    }),
    [medsBySlot]
  );
  const [prevAllDoneBySlot, setPrevAllDoneBySlot] = useState<Record<UiSlot, boolean>>({
    morning: false,
    lunch: false,
    dinner: false,
    night: false,
  });

  useEffect(() => {
    const nextTokens: Partial<Record<UiSlot, number>> = {};
    TIME_SLOTS.forEach((slot) => {
      if (!prevAllDoneBySlot[slot.key] && allDoneBySlot[slot.key]) {
        nextTokens[slot.key] = Date.now();
      }
    });
    if (Object.keys(nextTokens).length > 0) {
      setPawStampTokenBySlot((prev) => ({ ...prev, ...nextTokens }));
    }
    setPrevAllDoneBySlot(allDoneBySlot);
  }, [allDoneBySlot, prevAllDoneBySlot]);

  const currentSlot = getCurrentUiSlot();
  void currentSlot;

  const characterMessage = (() => {
    if (lastActiveSlot && allDoneBySlot[lastActiveSlot]) {
      return COMPLETION_MESSAGES[lastActiveSlot];
    }
    if (latestMood) {
      return MOOD_MESSAGES[String(latestMood)];
    }
    return greetingMessage;
  })();
  const bubbleBaseColor = latestMood ? MOOD_COLORS[latestMood] : "#F3FAFF";
  const bubbleColor = latestMood ? `${bubbleBaseColor}55` : bubbleBaseColor;
  const bubbleBorderColor = latestMood ? `${bubbleBaseColor}88` : "#CDE2F2";
  const bubbleTextColor = "#3a3228";

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
    const pageWidth = firstPage?.clientWidth ?? container.clientWidth;
    container.scrollTo({ left: pageWidth * index, behavior: "smooth" });
    setMoodSwipeIndex(index);
  };

  const scrollMedToIndex = (index: number) => {
    if (!medSwipeRef.current) return;
    const container = medSwipeRef.current;
    const firstPage = container.firstElementChild as HTMLElement | null;
    const pageWidth = firstPage?.clientWidth ?? container.clientWidth;
    container.scrollTo({ left: pageWidth * index, behavior: "smooth" });
    setMedSwipeIndex(index);
  };

  // ── 토스트 상태 ──
  const [toast, setToast] = useState("");
  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }, []);

  // 에러를 토스트로 대체
  useEffect(() => {
    if (error) {
      // 409 충돌은 조용히 무시
      if (!error.includes("MOOD_ALREADY_RECORDED") && !error.includes("409")) {
        showToast(error);
      }
      setError("");
    }
  }, [error, showToast]);

  return (
    <div
      aria-busy={loading}
      style={{
        minHeight: "100vh",
        background: "#F5F5F5",
        color: "#2C2C2C",
        padding: "16px",
        display: "flex",
        justifyContent: "center",
        opacity: pageLeaving ? 0 : 1,
        transition: "opacity 0.2s ease",
      }}
    >
      <style>{`
        .swipeContainer::-webkit-scrollbar {
          display: none;
        }
        .med-list::-webkit-scrollbar { width: 4px; }
        .med-list::-webkit-scrollbar-track { background: #F5F5F5; border-radius: 2px; }
        .med-list::-webkit-scrollbar-thumb { background: #99A988; border-radius: 2px; }
        @keyframes mood-shake {
          0%,100%{ transform: translateX(0); }
          20%{ transform: translateX(-4px); }
          40%{ transform: translateX(4px); }
          60%{ transform: translateX(-4px); }
          80%{ transform: translateX(4px); }
        }
        @keyframes mood-sob {
          0%,100%{ transform: translateY(0); }
          50%{ transform: translateY(4px); }
        }
        @keyframes mood-worry {
          0%,100%{ transform: rotate(0deg); }
          25%{ transform: rotate(-8deg); }
          75%{ transform: rotate(8deg); }
        }
        @keyframes mood-neutral {
          0%,100%{ transform: translateY(0); }
          50%{ transform: translateY(-2px); }
        }
        @keyframes mood-bounce {
          0%,100%{ transform: translateY(0); }
          40%{ transform: translateY(-6px); }
          60%{ transform: translateY(-4px); }
        }
        @keyframes mood-happy {
          0%,100%{ transform: rotate(0deg) scale(1); }
          25%{ transform: rotate(-10deg) scale(1.05); }
          75%{ transform: rotate(10deg) scale(1.05); }
        }
        @keyframes mood-spin {
          0%{ transform: translateY(0) rotate(0deg) scale(1); }
          50%{ transform: translateY(-10px) rotate(360deg) scale(1.12); }
          100%{ transform: translateY(0) rotate(360deg) scale(1); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pawStamp {
          0% { opacity: 0; transform: translate(-50%,-50%) rotate(-15deg) scale(3); }
          20% { opacity: 0.6; transform: translate(-50%,-50%) rotate(-15deg) scale(1.1); }
          40% { opacity: 0.35; transform: translate(-50%,-50%) rotate(-15deg) scale(1); }
          100% { opacity: 0.35; transform: translate(-50%,-50%) rotate(-15deg) scale(1); }
        }
      `}</style>

      {loading ? <MainPageSkeleton /> : <div style={{ width: "100%", maxWidth: 460 }}>
        {/* ── 헤더 카드 ── */}
        <div style={{
          ...cardStyle,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          animation: "fadeSlideUp 0.4s ease-out both",
          animationDelay: "0ms",
        }}>
          <button style={topButtonStyle} onClick={() => navigateWithFade("/diary")}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 16px rgba(153,169,136,0.45)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 12px rgba(153,169,136,0.35)"; }}
            onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.96)"; }}
            onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
          >일기</button>
          <button
            style={{
              background: "transparent",
              border: "none",
              color: "#2C2C2C",
              padding: 0,
              cursor: "pointer",
              fontSize: 16,
              transition: "opacity 0.15s ease",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.7"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
            onClick={() => navigateWithFade("/appointments")}
          >
            {nextAppointment ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <span
                  style={{
                    background: "#F0EDE3",
                    color: "#7A7040",
                    borderRadius: 999,
                    padding: "2px 10px",
                    fontSize: 12,
                    fontWeight: 700,
                    lineHeight: 1.4,
                  }}
                >
                  {nextAppointment.dDay}
                </span>
                <span style={{ fontSize: 19, fontWeight: 500, lineHeight: 1.2, color: "#2C2C2C" }}>
                  {nextAppointment.hospitalName ?? nextAppointment.dateLabel}
                </span>
                <span style={{ fontSize: 13, color: "#8A8A8A", lineHeight: 1.3 }}>
                  {nextAppointment.hospitalName
                    ? `${nextAppointment.dateLabel}${nextAppointment.timeLabel ? ` · ${nextAppointment.timeLabel}` : ""}`
                    : nextAppointment.timeLabel ?? "시간 미정"}
                </span>
              </div>
            ) : (
              "진료 없음"
            )}
          </button>
          <button style={topButtonStyle} onClick={() => navigateWithFade("/mypage")}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 16px rgba(153,169,136,0.45)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 12px rgba(153,169,136,0.35)"; }}
            onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.96)"; }}
            onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
          >내 정보</button>
        </div>

        {/* ── 캐릭터 + 기분 카드 ── */}
        <div style={{
          ...cardStyle,
          overflow: "hidden",
          paddingTop: 32,
          paddingBottom: 32,
          animation: "fadeSlideUp 0.4s ease-out both",
          animationDelay: "80ms",
        }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
            <div
              style={{
                position: "relative",
                background: bubbleColor,
                border: `1px solid ${bubbleBorderColor}`,
                borderRadius: 16,
                padding: "10px 14px",
                maxWidth: "88%",
                textAlign: "center",
                fontWeight: 600,
                lineHeight: 1.6,
                color: bubbleTextColor,
                boxShadow: "0 6px 16px rgba(137,175,207,0.18)",
                zIndex: 1,
              }}
            >
              {characterMessage}
              <span
                style={{
                  position: "absolute",
                  left: "52%",
                  bottom: -15,
                  width: 18,
                  height: 12,
                  borderRadius: 999,
                  border: `1px solid ${bubbleBorderColor}`,
                  background: bubbleColor,
                  transform: "translateX(-50%)",
                  pointerEvents: "none",
                }}
              />
              <span
                style={{
                  position: "absolute",
                  left: "58%",
                  bottom: -29,
                  width: 10,
                  height: 8,
                  borderRadius: 999,
                  border: `1px solid ${bubbleBorderColor}`,
                  background: bubbleColor,
                  transform: "translateX(-50%)",
                  pointerEvents: "none",
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: 16, textAlign: "center" }}>
            <img
              src={characterImage}
              alt="선택 캐릭터"
              onClick={() => navigateWithFade("/chat")}
              style={{
                width: 180,
                maxWidth: "70%",
                objectFit: "contain",
                margin: "0 auto",
                display: "block",
                cursor: "pointer",
                transition: "transform 0.2s ease",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLImageElement).style.transform = "scale(1.04) translateY(-4px)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLImageElement).style.transform = "scale(1) translateY(0)"; }}
            />
          </div>

          <div
            ref={moodSwipeRef}
            className="swipeContainer"
            style={{
              ...swipeContainerStyle,
              overflowX: "auto",
              overflowY: "hidden",
              paddingTop: 12,
              paddingBottom: 12,
            }}
            onScroll={updateMoodIndicator}
          >
            {TIME_SLOTS.map((slot) => (
              <div key={slot.key} style={swipePageStyle}>
                <h3 style={{ margin: "0 0 8px", fontSize: 14, lineHeight: 1.3, paddingTop: 2 }}>오늘의 {slot.label} 기분</h3>

                <div style={{ display: "flex", gap: "6px", flexWrap: "nowrap", justifyContent: "center", width: "max-content", margin: "0 auto" }}>
                  {Object.entries(MOOD_EMOJI).map(([level, emoji]) => {
                    const numeric = Number(level);
                    const selected = todayMoods[slot.key] === numeric;
                    const animated = animatedEmoji?.slot === slot.key && animatedEmoji.level === numeric;
                    return (
                      <button
                        key={`${slot.key}-${level}`}
                        onClick={() => handleMoodClick(slot.key, numeric)}
                        disabled={loading || isSavingMood}
                        style={getEmojiButtonStyle(numeric, selected)}
                      >
                        <span
                          key={`${slot.key}-${level}-${animated ? animatedEmoji?.nonce : 0}`}
                          style={{
                            display: "inline-block",
                            animation: animated ? EMOJI_ANIMATIONS[numeric] : "none",
                          }}
                        >
                          {emoji}
                        </span>
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

        {/* ── 복약 카드 ── */}
        <div style={{
          ...cardStyle,
          animation: "fadeSlideUp 0.4s ease-out both",
          animationDelay: "160ms",
        }}>
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
                    display: "flex",
                    flexDirection: "column",
                    opacity: allDone && slot.key !== lastActiveSlot ? 0.5 : 1,
                    filter: allDone && slot.key !== lastActiveSlot ? "grayscale(40%)" : "none",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <h3 style={{ margin: 0, fontSize: 15, fontWeight: 800, color: "#3a3228" }}>오늘의 {slot.label} 약</h3>
                    <button style={topButtonStyle} onClick={() => navigateWithFade("/medications/add")}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 16px rgba(153,169,136,0.45)"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 4px 12px rgba(153,169,136,0.35)"; }}
                      onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.96)"; }}
                      onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
                    >약 추가</button>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <div style={{ minWidth: 74, fontSize: 13, color: "#a09070" }}>
                      {completeCount} / {totalCount}
                    </div>
                    <div style={{ flex: 1, height: 8, borderRadius: 999, background: "#E8E8E8", overflow: "hidden" }}>
                      <div
                        style={{
                          width: total === 0 ? "0%" : `${(completed / total) * 100}%`,
                          height: "100%",
                          background: "#99A988",
                          transition: "width 0.4s ease",
                        }}
                      />
                    </div>
                  </div>

                  {allDone && (
                    <div
                      key={`paw-${slot.key}-${pawStampTokenBySlot[slot.key]}`}
                      style={{
                        ...pawStampStyle,
                        animation: `pawStamp 0.6s ease-out ${pawStampTokenBySlot[slot.key] > 0 ? "forwards" : "none"}`,
                      }}
                    >
                      🐾
                    </div>
                  )}

                <div className="med-list" style={{ maxHeight: 200, overflowY: "auto", paddingRight: 2 }}>
                    {medications.map((med) => (
                      <div key={med.id} style={{ marginBottom: "6px" }}>
                        <div
                          onClick={() => !isSavingMedication && handleMedicationToggle(med.medicationId, med.checked, med.timeSlot)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 10,
                            padding: "8px",
                            borderRadius: "8px",
                            border: med.checked ? "1px solid #C5D4B8" : "1px solid #E8E8E8",
                            background: med.checked ? "#F0F5EE" : "#FFFFFF",
                            textDecoration: med.checked ? "line-through" : "none",
                            color: med.checked ? "#9aaa8a" : "#3a3228",
                            cursor: isSavingMedication ? "not-allowed" : "pointer",
                            opacity: isSavingMedication ? 0.6 : 1,
                            transition: "background 0.2s ease, border-color 0.2s ease, opacity 0.15s ease",
                          }}
                        >
                          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div
                              style={{
                                width: 22,
                                height: 22,
                                borderRadius: 6,
                                border: med.checked ? "none" : "2px solid #C5D4B8",
                                background: med.checked ? "#99A988" : "#FFFFFF",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexShrink: 0,
                                transition: "all 0.2s ease",
                              }}
                            >
                              {med.checked && (
                                <svg width="13" height="10" viewBox="0 0 13 10" fill="none">
                                  <path
                                    d="M1.5 5L5 8.5L11.5 1.5"
                                    stroke="white"
                                    strokeWidth="2.2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                  />
                                </svg>
                              )}
                            </div>
                            {med.name} {med.dosage}정
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMedicationDetailToggle(med);
                            }}
                            style={{
                              background: "rgba(153,169,136,0.1)",
                              border: "1px solid rgba(153,169,136,0.25)",
                              color: "#5a7a4a",
                              borderRadius: 10,
                              padding: "4px 12px",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: "pointer",
                              flexShrink: 0,
                            }}
                          >
                            {expandedMedicationId === med.medicationId ? "접기 ▲" : "더보기 ▼"}
                          </button>
                        </div>

                        {expandedMedicationId === med.medicationId && (
                          <div
                            style={{
                              marginTop: 8,
                              border: `1px solid ${COLORS.border}`,
                              borderRadius: 8,
                              background: COLORS.cardBg,
                              padding: 10,
                            }}
                          >
                            {loadingDetailByMedicationId[med.medicationId] ? (
                              <div style={{ display: "flex", justifyContent: "center", padding: "16px 0" }}>
                                <div
                                  style={{
                                    width: 20,
                                    height: 20,
                                    border: `2px solid ${COLORS.border}`,
                                    borderTop: `2px solid ${COLORS.button}`,
                                    borderRadius: "50%",
                                    animation: "spin 1s linear infinite",
                                  }}
                                />
                              </div>
                            ) : detailErrorByMedicationId[med.medicationId] ? (
                              <div style={{ color: COLORS.error, fontSize: 13 }}>
                                {detailErrorByMedicationId[med.medicationId]}
                              </div>
                            ) : (
                              <>
                                {(detailByMedicationId[med.medicationId]?.item_image ?? med.itemImage) ? (
                                  <img
                                    src={detailByMedicationId[med.medicationId]?.item_image ?? med.itemImage ?? ""}
                                    alt={med.name}
                                    style={{ width: "100%", maxHeight: 200, objectFit: "contain", borderRadius: 8 }}
                                  />
                                ) : (
                                  <div
                                    style={{
                                      width: "100%",
                                      maxHeight: 200,
                                      minHeight: 120,
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "center",
                                      fontSize: 64,
                                    }}
                                  >
                                    💊
                                  </div>
                                )}

                                <div style={{ marginTop: 10 }}>
                                  <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: 4 }}>효능/효과</div>
                                  <div style={{ color: COLORS.subText, fontSize: 13, lineHeight: 1.5 }}>
                                    {detailByMedicationId[med.medicationId]?.efcy_qesitm ?? "정보가 없습니다."}
                                  </div>
                                </div>

                                <div style={{ marginTop: 10 }}>
                                  <div style={{ fontWeight: 700, color: COLORS.text, marginBottom: 4 }}>복용법</div>
                                  <div style={{ color: COLORS.subText, fontSize: 13, lineHeight: 1.5 }}>
                                    {detailByMedicationId[med.medicationId]?.use_method_qesitm ?? "정보가 없습니다."}
                                  </div>
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    ))}

                  {medications.length === 0 && (
                    <div style={{ fontSize: 14, color: "#757575" }}>등록된 약이 없습니다.</div>
                  )}
                </div>
                {allDone && slot.key === lastActiveSlot && (
                  <div
                    style={{
                      background: "#99A988",
                      borderRadius: 14,
                      padding: "14px 16px",
                      textAlign: "center",
                      fontWeight: 800,
                      fontSize: 16,
                      color: "#FFFFFF",
                      marginTop: 16,
                    }}
                  >
                    🎉 복약 완료를 축하해요!
                  </div>
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

        </div>

      </div>}

      {/* ── 토스트 ── */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: 32,
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(44,44,44,0.88)",
            color: "#fff",
            padding: "10px 20px",
            borderRadius: 20,
            fontSize: 14,
            zIndex: 200,
            whiteSpace: "nowrap",
            animation: "toastIn 0.25s ease-out both",
            pointerEvents: "none",
          }}
        >
          {toast}
        </div>
      )}
    </div>
  );
}
