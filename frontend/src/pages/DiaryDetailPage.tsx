import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { createDiaryText, getDiaryByDate, updateDiaryEntry } from "../apis/diary";
import { upsertMood } from "../apis/moods";
import Button from "../components/Button";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS, MOOD_COLORS, MOOD_EMOJI_MAP, TIME_SLOT_LABELS } from "../constants/theme";
import { formatDateLabel } from "../utils/date";

const ALL_SLOTS = ["MORNING", "LUNCH", "EVENING", "BEDTIME"] as const;
type TimeSlot = (typeof ALL_SLOTS)[number];


export function DiaryDetailPage() {
  const { entryDate = "" } = useParams<{ entryDate: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const isEditMode = searchParams.get("mode") === "edit";
  const editEntryId = Number(searchParams.get("entryId") || 0) || null;

  const [entries, setEntries] = useState<Array<{ entryId: number; source: string; title: string; content: string; createdAt: string }>>([]);
  const [moods, setMoods] = useState<Array<{ mood_level: number; time_slot?: string }>>([]);
  const [editingSlot, setEditingSlot] = useState<TimeSlot | null>(null);
  const [moodSaving, setMoodSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const firstEntry = useMemo(() => entries[0] ?? null, [entries]);

  const fetchDiary = useCallback(async () => {
    if (!entryDate) return;
    try {
      setLoading(true);
      setError(null);
      const result = await getDiaryByDate(entryDate);
      if (!result) {
        setEntries([]);
        setMoods([]);
        return;
      }
      setEntries(result.entries ?? []);
      setMoods(result.moods ?? []);
      if (isEditMode && result.entries?.[0]) {
        setTitle(result.entries[0].title ?? "");
        setContent(result.entries[0].content ?? "");
      }
    } catch (err) {
      setEntries([]);
      setMoods([]);
      setError(err instanceof Error ? err.message : "일기 데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [entryDate, isEditMode]);

  useEffect(() => {
    void fetchDiary();
  }, [fetchDiary]);

  const handleSave = async () => {
    if (!title.trim() || !content.trim()) {
      setSaveError("제목과 내용을 모두 입력해주세요.");
      return;
    }
    if (!entryDate) return;

    try {
      setSaveLoading(true);
      setSaveError(null);
      if (isEditMode && editEntryId) {
        await updateDiaryEntry(entryDate, editEntryId, { title, content });
      } else {
        await createDiaryText(entryDate, { title, content });
      }
      navigate("/diary");
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <main style={{ minHeight: "100vh", background: COLORS.background, padding: 16, display: "flex", justifyContent: "center" }}>
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
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div>
          <p style={{ margin: 0, fontSize: 11, color: COLORS.buttonBg, fontWeight: 700 }}>{entryDate}</p>
          <h1 style={{ margin: 0, fontSize: 20 }}>{entryDate ? formatDateLabel(entryDate) : "일기 상세"}</h1>
        </div>
      </div>
      <section style={{ background: COLORS.cardBg, borderRadius: 12, border: `1px solid ${COLORS.border}`, padding: "10px 12px" }}>
        <p style={{ margin: "0 0 8px", fontSize: 12, color: COLORS.subText, fontWeight: 700 }}>오늘의 기분</p>
        <div style={{ display: "flex", gap: "12px" }}>
          {ALL_SLOTS.map((slot) => {
            const mood = moods.find((m) => m.time_slot === slot);
            const level = mood?.mood_level ?? null;
            const isEditing = editingSlot === slot;
            return (
              <div key={slot} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                <div
                  onClick={() => setEditingSlot(isEditing ? null : slot)}
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "50%",
                    background: level ? (MOOD_COLORS[level] ?? COLORS.border) : "#D9D9D9",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    fontSize: level ? 16 : 12,
                    border: isEditing ? "2px solid #99A988" : "2px solid transparent",
                    transition: "all 0.15s ease",
                  }}
                >
                  {level ? MOOD_EMOJI_MAP[level] : "?"}
                </div>
                <span style={{ fontSize: "10px", color: COLORS.subText }}>
                  {TIME_SLOT_LABELS[slot]}
                </span>
              </div>
            );
          })}
        </div>

        {editingSlot && (
          <div style={{
            display: "flex",
            gap: 6,
            justifyContent: "center",
            marginTop: 10,
            padding: "8px 6px",
            background: "#FAFAFA",
            borderRadius: 12,
            border: `1px solid ${COLORS.border}`,
          }}>
            {[1, 2, 3, 4, 5, 6, 7].map((lv) => {
              const currentLevel = moods.find((m) => m.time_slot === editingSlot)?.mood_level ?? null;
              return (
                <button
                  key={lv}
                  disabled={moodSaving}
                  onClick={async () => {
                    if (!entryDate) return;
                    setMoodSaving(true);
                    try {
                      await upsertMood({ log_date: entryDate, time_slot: editingSlot, mood_level: lv });
                      setMoods((prev) => {
                        const filtered = prev.filter((m) => m.time_slot !== editingSlot);
                        return [...filtered, { mood_level: lv, time_slot: editingSlot }];
                      });
                      setEditingSlot(null);
                    } catch { /* ignore */ } finally {
                      setMoodSaving(false);
                    }
                  }}
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: "50%",
                    border: currentLevel === lv ? `2px solid ${MOOD_COLORS[lv]}` : "1px solid #eee",
                    background: currentLevel === lv ? `${MOOD_COLORS[lv]}33` : "#fff",
                    fontSize: 16,
                    cursor: "pointer",
                    padding: 0,
                    transition: "all 0.15s ease",
                  }}
                >
                  {MOOD_EMOJI_MAP[lv]}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {loading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchDiary()} /> : null}

      {!loading && !error && firstEntry && !isEditMode ? (
        <section style={{ background: COLORS.cardBg, borderRadius: 16, border: `1px solid ${COLORS.border}`, padding: 20 }}>
          <h2 style={{ margin: "0 0 12px", fontSize: 18 }}>▶ {firstEntry.title}</h2>
          <p style={{ margin: 0, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{firstEntry.content}</p>
          <p style={{ margin: "10px 0 0", color: COLORS.subText, fontSize: 12 }}>작성 방식: {firstEntry.source}</p>
          <div style={{ marginTop: 12 }}>
            <Button variant="secondary" onClick={() => navigate(`/diary/${entryDate}?mode=edit&entryId=${firstEntry.entryId}`)}>
              수정하기
            </Button>
          </div>
        </section>
      ) : null}

      {(!firstEntry || isEditMode) && (
        <section style={{ background: COLORS.cardBg, borderRadius: 16, border: `1px solid ${COLORS.border}`, padding: 20, display: "grid", gap: 12 }}>
          <h2 style={{ margin: 0, fontSize: 16 }}>{isEditMode ? "일기 수정" : "일기 작성"}</h2>

          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="제목을 입력하세요"
            style={{ width: "100%", padding: "12px 14px", border: `1px solid ${COLORS.border}`, borderRadius: 10, boxSizing: "border-box" }}
          />
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="내용을 입력하세요"
            rows={10}
            style={{ width: "100%", padding: "12px 14px", border: `1px solid ${COLORS.border}`, borderRadius: 10, boxSizing: "border-box", resize: "vertical" }}
          />
          {saveError ? <p style={{ margin: 0, color: COLORS.error, fontSize: 13 }}>{saveError}</p> : null}
          <Button variant="primary" onClick={() => void handleSave()} loading={saveLoading} fullWidth>
            {isEditMode ? "수정 저장" : "저장하기"}
          </Button>
        </section>
      )}
      </div>
    </main>
  );
}
