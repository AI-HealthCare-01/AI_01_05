import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { tokenStorage } from "../api/client";
import { deleteDiaryEntry, getDiaryByDate, getDiaryCalendar, type DiaryCalendarResponse } from "../api/diary";
import Button from "../components/Button";
import { Calendar } from "../components/Calendar";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS, MOOD_COLORS, TIME_SLOT_LABELS, WRITE_METHOD_LABELS } from "../constants/theme";
import { formatDateLabel } from "../utils/date";

function shiftMonth(year: number, month: number, delta: number) {
  const base = new Date(year, month - 1 + delta, 1);
  return { year: base.getFullYear(), month: base.getMonth() + 1 };
}

export function DiaryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const today = useMemo(() => new Date(), []);
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [data, setData] = useState<DiaryCalendarResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<{
    entryId: number;
    source: string;
    title: string;
    content: string;
    createdAt: string;
  } | null>(null);
  const [diaryLoading, setDiaryLoading] = useState(false);
  const [diaryError, setDiaryError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetFull, setSheetFull] = useState(false);

  const fetchCalendar = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getDiaryCalendar(year, month);
      setData(result);
    } catch (err) {
      if (err instanceof Error && err.name === "SessionExpiredError") {
        setError("인증 토큰이 없거나 만료되었습니다. 아래에 access token을 입력해주세요.");
      } else {
        setError("캘린더 데이터를 불러오지 못했습니다.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [month, year]);

  const fetchSelectedDateDiary = useCallback(async (entryDate: string) => {
    try {
      setDiaryLoading(true);
      setDiaryError(null);
      setSelectedEntry(null);
      const result = await getDiaryByDate(entryDate);
      if (!result) {
        setSelectedEntry(null);
        return;
      }
      setSelectedEntry(result.entries[0] ?? null);
    } catch (err) {
      setDiaryError(err instanceof Error ? err.message : "일기를 불러오지 못했습니다.");
    } finally {
      setDiaryLoading(false);
    }
  }, []);

  const openWriteModal = useCallback(() => {
    if (!selectedDate) return;
    navigate(`/diary/${selectedDate}`);
  }, [navigate, selectedDate]);

  useEffect(() => {
    void fetchCalendar();
  }, [fetchCalendar]);

  const removeSelectedEntry = async () => {
    if (!selectedDate || !selectedEntry) return;
    if (!window.confirm("일기를 삭제할까요?")) return;
    await deleteDiaryEntry(selectedDate, selectedEntry.entryId);
    setSelectedEntry(null);
    await fetchCalendar();
  };

  const handleDateClick = useCallback(
    (entryDate: string) => {
      setSelectedDate(entryDate);
      setSheetOpen(true);
      setSheetFull(false);
      void fetchSelectedDateDiary(entryDate);
    },
    [fetchSelectedDateDiary],
  );

  const tab = location.pathname.startsWith("/report") ? "report" : "diary";
  const selectedMoods = useMemo(
    () =>
      (data?.days.find((day) => day.date === selectedDate)?.moods ?? []).map((mood) => ({
        mood_level: mood.mood_level,
        time_slot: mood.time_slot,
      })),
    [data?.days, selectedDate],
  );
  const todayStr = new Date().toISOString().slice(0, 10);
  const isFuture = selectedDate ? selectedDate > todayStr : false;

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "grid", gap: 12 }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "15px",
          color: COLORS.subText,
          fontWeight: 600,
          padding: "0 0 16px 0",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
      </button>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>나의 일기장</h1>
        <div
          style={{
            display: "flex",
            background: COLORS.overlay,
            borderRadius: "20px",
            padding: "4px",
            gap: "2px",
          }}
        >
          {[
            { key: "diary", label: "일기", path: "/diary" },
            { key: "report", label: "리포트", path: "/report" },
          ].map(({ key, label, path }) => (
            <button
              key={key}
              onClick={() => {
                navigate(path);
                window.scrollTo(0, 0);
              }}
              style={{
                padding: "6px 16px",
                borderRadius: "16px",
                border: "none",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                fontFamily: "inherit",
                background: tab === key ? COLORS.tabActiveBg : "transparent",
                color: tab === key ? COLORS.tabActiveText : COLORS.tabInactiveText,
                transition: "all 0.15s",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchCalendar()} /> : null}
      {error?.includes("인증 토큰") ? (
        <section style={{ display: "grid", gap: 8, border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff" }}>
          <input
            value={tokenInput}
            onChange={(event) => setTokenInput(event.target.value)}
            placeholder="Bearer 제외한 access token 입력"
            style={{ padding: 10, border: "1px solid #ccc", borderRadius: 8 }}
          />
          <Button
            type="button"
            onClick={() => {
              tokenStorage.setAccessToken(tokenInput.trim());
              tokenStorage.setRefreshToken("dev-refresh");
              void fetchCalendar();
            }}
          >
            토큰 저장 후 다시 시도
          </Button>
        </section>
      ) : null}
      {!isLoading && !error && data ? (
        <Calendar
          year={year}
          month={month}
          days={data.days.map((d) => ({
            date: d.date,
            moods: (d.moods ?? []).map((m) => ({ mood_level: m.mood_level, time_slot: m.time_slot })),
          }))}
          onPrevMonth={() => {
            const next = shiftMonth(year, month, -1);
            setYear(next.year);
            setMonth(next.month);
            setSelectedDate(null);
            setSelectedEntry(null);
            setSheetOpen(false);
            setSheetFull(false);
          }}
          onNextMonth={() => {
            const next = shiftMonth(year, month, 1);
            setYear(next.year);
            setMonth(next.month);
            setSelectedDate(null);
            setSelectedEntry(null);
            setSheetOpen(false);
            setSheetFull(false);
          }}
          onSelectDate={handleDateClick}
          selectedDate={selectedDate ?? today.toISOString().slice(0, 10)}
        />
      ) : null}
      {!isLoading && !error && data && data.days.length === 0 ? <EmptyState message="기록된 일기가 없습니다." /> : null}
      {selectedDate ? (
        <>
          {sheetOpen ? (
            <div
              onClick={() => {
                setSheetOpen(false);
                setSheetFull(false);
              }}
              style={{
                position: "fixed",
                inset: 0,
                zIndex: 30,
                background: sheetFull ? "rgba(0,0,0,0.3)" : "transparent",
                transition: "background 0.3s",
              }}
            />
          ) : null}

          <div
            style={{
              position: "fixed",
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 40,
              background: COLORS.cardBg,
              borderRadius: "20px 20px 0 0",
              boxShadow: "0 -4px 24px rgba(0,0,0,0.12)",
              transform: sheetOpen ? "translateY(0)" : "translateY(100%)",
              transition: "transform 0.35s cubic-bezier(0.32, 0.72, 0, 1), max-height 0.3s ease",
              maxHeight: sheetFull ? "92vh" : "52vh",
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
              touchAction: "pan-y",
            }}
          >
            <div
              onClick={() => setSheetFull((prev) => !prev)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "12px 0 8px",
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "36px",
                  height: "4px",
                  borderRadius: "2px",
                  background: COLORS.border,
                  marginBottom: "12px",
                }}
              />
              <div
                style={{
                  width: "100%",
                  paddingLeft: "20px",
                  paddingRight: "20px",
                  paddingBottom: "12px",
                  boxSizing: "border-box",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  borderBottom: `1px solid ${COLORS.border}`,
                }}
              >
                <h2 style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: COLORS.text }}>{formatDateLabel(selectedDate)}</h2>
                <div style={{ display: "flex", gap: "6px" }}>
                  {selectedEntry ? (
                    <>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          navigate(`/diary/${selectedDate}?mode=edit&entryId=${selectedEntry.entryId}`);
                        }}
                        style={{
                          background: "transparent",
                          color: COLORS.text,
                          border: `1px solid ${COLORS.border}`,
                          borderRadius: "999px",
                          padding: "7px 14px",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        수정
                      </button>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          void removeSelectedEntry();
                        }}
                        style={{
                          background: "transparent",
                          color: COLORS.error,
                          border: `1px solid ${COLORS.error}`,
                          borderRadius: "999px",
                          padding: "7px 14px",
                          fontSize: "12px",
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        삭제
                      </button>
                    </>
                  ) : !isFuture ? (
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        openWriteModal();
                      }}
                      style={{
                        background: COLORS.buttonBg,
                        color: COLORS.buttonText,
                        border: "none",
                        borderRadius: "999px",
                        padding: "7px 14px",
                        fontSize: "12px",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      + 작성하기
                    </button>
                  ) : null}
                </div>
              </div>
            </div>

            <div style={{ overflowY: "auto", padding: "16px 20px 32px", flex: 1 }}>
              {diaryLoading ? <Loading message="일기를 불러오는 중..." /> : null}
              {!diaryLoading && diaryError ? <ErrorMessage message={diaryError} onRetry={() => void fetchSelectedDateDiary(selectedDate)} /> : null}

              {!diaryLoading && !diaryError && isFuture ? (
                <div style={{ textAlign: "center", padding: "24px 0" }}>
                  <p style={{ color: COLORS.subText, fontSize: "14px", margin: 0 }}>아직 작성할 수 없는 날짜예요. 😊</p>
                </div>
              ) : null}

              {!diaryLoading && !diaryError && !isFuture && selectedEntry ? (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                    <span style={{ color: COLORS.buttonBg }}>▶</span>
                    <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 700, flex: 1, color: COLORS.text }}>{selectedEntry.title}</h3>
                    <span style={{ fontSize: "11px", color: COLORS.subText, background: COLORS.background, padding: "2px 8px", borderRadius: "20px" }}>
                      {WRITE_METHOD_LABELS[selectedEntry.source] ?? selectedEntry.source}
                    </span>
                  </div>
                  <p style={{ fontSize: "14px", lineHeight: 1.8, color: COLORS.text, margin: "0 0 16px", whiteSpace: "pre-wrap" }}>{selectedEntry.content}</p>

                  {selectedMoods.length > 0 ? (
                    <div style={{ paddingTop: "14px", borderTop: `1px solid ${COLORS.border}` }}>
                      <p style={{ margin: "0 0 10px", fontSize: "11px", fontWeight: 700, color: COLORS.subText }}>오늘의 기분</p>
                      <div style={{ display: "flex", gap: "12px" }}>
                        {selectedMoods.map((mood, index) => (
                          <div key={`${mood.time_slot}-${index}`} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                            <div
                              style={{
                                width: "28px",
                                height: "28px",
                                borderRadius: "50%",
                                background: MOOD_COLORS[mood.mood_level] ?? COLORS.border,
                              }}
                            />
                            <span style={{ fontSize: "10px", color: COLORS.subText }}>{TIME_SLOT_LABELS[mood.time_slot ?? ""] ?? mood.time_slot}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              ) : null}

              {!diaryLoading && !diaryError && !isFuture && !selectedEntry ? (
                <div style={{ textAlign: "center", padding: "24px 0" }}>
                  <p style={{ color: COLORS.subText, fontSize: "14px", marginBottom: "16px" }}>이 날짜에는 작성된 일기가 없습니다.</p>
                  <Button onClick={openWriteModal}>일기 쓰기</Button>
                </div>
              ) : null}
            </div>
          </div>
        </>
      ) : null}
    </main>
  );
}
