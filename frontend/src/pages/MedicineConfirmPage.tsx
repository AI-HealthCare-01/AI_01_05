import type { CSSProperties } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postHomeMedicationToday, type MedicationTimeSlot } from "../api/home";
import { Button } from "../components/Button";
import { EmptyState } from "../components/CommonUI";
import { COLORS } from "../constants/theme";
import { useMedicationFlow } from "../store/MedicationFlowContext";
import type { MedicineDraftItem } from "../types/medicine";

const toolbarKeyframes = `
@keyframes toolbarIn {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes successPop {
  0%   { opacity: 0; transform: translateX(-50%) scale(0.8); }
  60%  { opacity: 1; transform: translateX(-50%) scale(1.05); }
  100% { opacity: 1; transform: translateX(-50%) scale(1); }
}
`;

/** 수출명 이후 텍스트 제거 후 반환 */
function trimDrugName(name: string): string {
  return name.replace(/[(（]?수출명[：:].*/i, "").trim();
}

const TIME_SLOT_OPTIONS = [
  { value: "MORNING", label: "아침" },
  { value: "LUNCH", label: "점심" },
  { value: "EVENING", label: "저녁" },
  { value: "BEDTIME", label: "자기전" },
  { value: "OTHER", label: "기타" },
];

const DEFAULT_TIME_SLOTS: Record<number, string[]> = {
  1: ["MORNING"],
  2: ["MORNING", "EVENING"],
  3: ["MORNING", "LUNCH", "EVENING"],
};

const HOME_TIME_SLOTS: MedicationTimeSlot[] = ["MORNING", "LUNCH", "EVENING", "BEDTIME"];

const cardStyle: CSSProperties = {
  background: COLORS.cardBg,
  borderRadius: 20,
  border: `1px solid ${COLORS.border}`,
  padding: 16,
  marginBottom: 12,
};

function Stepper({
  value,
  onChange,
  min = 1,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Button variant="secondary" onClick={() => onChange(Math.max(min, value - 1))} style={{ minWidth: 36, padding: "6px 10px" }}>
        －
      </Button>
      <span style={{ minWidth: 36, textAlign: "center", fontWeight: 700 }}>{value}</span>
      <Button variant="secondary" onClick={() => onChange(value + 1)} style={{ minWidth: 36, padding: "6px 10px" }}>
        ＋
      </Button>
    </div>
  );
}

function EditCard({
  item,
  onConfirm,
  onCancel,
}: {
  item: MedicineDraftItem;
  onConfirm: (updated: MedicineDraftItem) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState<MedicineDraftItem>({ ...item });
  const [manualSlots, setManualSlots] = useState(false);

  const setFrequency = (v: number) => {
    const next = { ...draft, daily_frequency: v };
    if (!manualSlots && DEFAULT_TIME_SLOTS[v]) {
      next.time_slots = DEFAULT_TIME_SLOTS[v];
    }
    setDraft(next);
  };

  const toggleSlot = (slot: string) => {
    setManualSlots(true);
    setDraft((prev) => ({
      ...prev,
      time_slots: prev.time_slots.includes(slot)
        ? prev.time_slots.filter((s) => s !== slot)
        : [...prev.time_slots, slot],
    }));
  };

  return (
    <div
      style={{
        ...cardStyle,
        border: `2px solid ${COLORS.button}`,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 16, color: COLORS.text, marginBottom: 12, wordBreak: "keep-all", overflowWrap: "break-word" }}>
        {trimDrugName(draft.item_name)}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: COLORS.subText }}>복용시작일</span>
          <input
            type="date"
            value={draft.start_date}
            onChange={(e) => setDraft({ ...draft, start_date: e.target.value })}
            style={{
              border: `1px solid ${COLORS.border}`,
              borderRadius: 12,
              padding: "8px 12px",
              fontSize: 13,
            }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: COLORS.subText }}>투약량(정)</span>
          <Stepper value={draft.dose_per_intake} onChange={(v) => setDraft({ ...draft, dose_per_intake: v })} />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: COLORS.subText }}>1일 횟수</span>
          <Stepper value={draft.daily_frequency} onChange={setFrequency} />
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 13, color: COLORS.subText }}>복용 일수</span>
          <Stepper value={draft.total_days} onChange={(v) => setDraft({ ...draft, total_days: v })} />
        </div>

        <div>
          <div style={{ fontSize: 13, color: COLORS.subText, marginBottom: 6 }}>복용시간</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {TIME_SLOT_OPTIONS.map(({ value, label }) => {
              const active = draft.time_slots.includes(value);
              return (
                <button
                  key={value}
                  onClick={() => toggleSlot(value)}
                  style={{
                    background: active ? COLORS.button : COLORS.cardBg,
                    color: active ? "#fff" : COLORS.text,
                    border: active ? "none" : `1px solid ${COLORS.border}`,
                    borderRadius: 20,
                    padding: "4px 12px",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <Button variant="secondary" onClick={onCancel} style={{ flex: 1 }}>
          취소
        </Button>
        <Button variant="primary" onClick={() => onConfirm(draft)} style={{ flex: 1 }}>
          확인
        </Button>
      </div>
    </div>
  );
}

function NormalCard({
  item,
  onEdit,
  deleteMode,
  checked,
  onCheck,
}: {
  item: MedicineDraftItem;
  onEdit: () => void;
  deleteMode: boolean;
  checked: boolean;
  onCheck: () => void;
}) {
  return (
    <div
      style={{
        ...cardStyle,
        display: "flex",
        gap: 10,
        background: checked ? COLORS.selectedCellBg : COLORS.cardBg,
        border: checked ? `1px solid ${COLORS.button}` : `1px solid ${COLORS.border}`,
      }}
    >
      {deleteMode && (
        <input
          type="checkbox"
          checked={checked}
          onChange={onCheck}
          aria-label={item.item_name}
          style={{ accentColor: COLORS.button, width: 16, height: 16, marginTop: 2, flexShrink: 0, cursor: "pointer" }}
        />
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontWeight: 700,
          fontSize: 16,
          color: COLORS.text,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}>
          {trimDrugName(item.item_name)}
        </div>
        <div style={{ fontSize: 12, color: COLORS.subText, marginTop: 2 }}>
          복용시작일: {item.start_date}
        </div>
        <div style={{ display: "flex", gap: 12, fontSize: 13, marginTop: 6 }}>
          <span>
            <span style={{ color: COLORS.subText }}>투약량 </span>
            <span style={{ fontWeight: 600 }}>{item.dose_per_intake}</span>
          </span>
          <span>
            <span style={{ color: COLORS.subText }}>횟수 </span>
            <span style={{ fontWeight: 600 }}>{item.daily_frequency}</span>
          </span>
          <span>
            <span style={{ color: COLORS.subText }}>일수 </span>
            <span style={{ fontWeight: 600 }}>{item.total_days}</span>
          </span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
          {item.time_slots.map((slot) => (
            <span
              key={slot}
              style={{
                background: COLORS.selectedCellBg,
                color: COLORS.button,
                borderRadius: 20,
                padding: "3px 10px",
                fontSize: 12,
              }}
            >
              {TIME_SLOT_OPTIONS.find((o) => o.value === slot)?.label ?? slot}
            </span>
          ))}
        </div>
      </div>
      {!deleteMode && (
        <Button variant="secondary" onClick={onEdit} style={{ alignSelf: "flex-start" }}>
          수정
        </Button>
      )}
    </div>
  );
}

export default function MedicineConfirmPage() {
  const navigate = useNavigate();
  const { medicinesDraft, updateDraft, removeDraft, clearDraft } = useMedicationFlow();

  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [deleteMode, setDeleteMode] = useState(false);
  const [checkedIndices, setCheckedIndices] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [successToast, setSuccessToast] = useState(false);

  const toggleCheck = (i: number) =>
    setCheckedIndices((prev) =>
      prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]
    );

  const toggleAll = () =>
    setCheckedIndices(
      checkedIndices.length === medicinesDraft.length
        ? []
        : medicinesDraft.map((_, i) => i)
    );

  const handleDelete = () => {
    removeDraft(checkedIndices);
    setCheckedIndices([]);
    setDeleteMode(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setErrors({});
    const nextErrors: Record<number, string> = {};
    for (let i = 0; i < medicinesDraft.length; i++) {
      try {
        const current = medicinesDraft[i];
        const selectedSlot =
          current.time_slots.find((slot): slot is MedicationTimeSlot =>
            HOME_TIME_SLOTS.includes(slot as MedicationTimeSlot)
          ) ?? "MORNING";

        await postHomeMedicationToday({
          medicationName: current.item_name,
          timeSlot: selectedSlot,
          dosage: current.dose_per_intake,
        });
      } catch {
        nextErrors[i] = `${medicinesDraft[i].item_name} 저장 실패`;
      }
    }
    setSaving(false);
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    clearDraft();
    setSuccessToast(true);
    setTimeout(() => navigate("/main"), 1200);
  };

  const handleCancel = () => {
    clearDraft();
    navigate("/medications/add");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: COLORS.background,
        padding: 16,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <style>{toolbarKeyframes}</style>
      <div style={{ width: "100%", maxWidth: 460, paddingBottom: 100 }}>
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            position: "relative",
            marginBottom: 16,
            background: deleteMode ? "#FFF3F3" : COLORS.cardBg,
            ...(deleteMode ? { animation: "toolbarIn 0.25s ease" } : {}),
          }}
        >
          {deleteMode ? (
            <>
              <span style={{ fontWeight: 700, color: COLORS.error }}>삭제 모드</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Button variant="secondary" onClick={() => { setDeleteMode(false); setCheckedIndices([]); }} style={{ fontSize: 12, padding: "6px 10px" }}>
                  취소
                </Button>
                <Button variant="secondary" onClick={toggleAll} style={{ fontSize: 12, padding: "6px 10px" }}>
                  전체 선택
                </Button>
                <Button variant="danger" onClick={handleDelete} disabled={checkedIndices.length === 0} style={{ fontSize: 12, padding: "6px 10px" }}>
                  선택 삭제
                </Button>
              </div>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate("/main")}
                style={{
                  position: "absolute",
                  left: 16,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: COLORS.text,
                  display: "flex",
                  alignItems: "center",
                  padding: 4,
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.1)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)"; }}
                onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.95)"; }}
                onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.1)"; }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9 22 9 12 15 12 15 22" />
                </svg>
              </button>
              <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
                <span style={{ fontWeight: 800, fontSize: 18, color: COLORS.text }}>추가할 약 목록</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Button
                  variant="primary"
                  onClick={() => navigate("/medications/search")}
                  style={{ fontSize: 12, padding: "6px 10px" }}
                >
                  + 추가
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setDeleteMode(true)}
                  style={{ fontSize: 12, padding: "6px 10px" }}
                >
                  삭제
                </Button>
              </div>
            </>
          )}
        </div>

        {medicinesDraft.length === 0 && (
          <EmptyState
            message="추가된 약이 없습니다"
            action={{ label: "약 검색하기", onClick: () => navigate("/medications/search") }}
          />
        )}

        {medicinesDraft.map((item, i) =>
          editIndex === i ? (
            <EditCard
              key={i}
              item={item}
              onConfirm={(updated) => { updateDraft(i, updated); setEditIndex(null); }}
              onCancel={() => setEditIndex(null)}
            />
          ) : (
            <div
              key={i}
              style={{
                transition: "all 0.2s ease",
                ...(deleteMode && checkedIndices.includes(i)
                  ? { outline: `2px solid ${COLORS.button}`, borderRadius: 20, background: COLORS.selectedCellBg }
                  : {}),
              }}
            >
              <NormalCard
                item={item}
                onEdit={() => setEditIndex(i)}
                deleteMode={deleteMode}
                checked={checkedIndices.includes(i)}
                onCheck={() => toggleCheck(i)}
              />
              {errors[i] && (
                <div style={{ color: COLORS.error, fontSize: 12, marginTop: -8, marginBottom: 8, paddingLeft: 4 }}>
                  {errors[i]}
                </div>
              )}
            </div>
          )
        )}

      </div>

      {successToast && (
        <div
          style={{
            position: "fixed",
            bottom: 90,
            left: "50%",
            background: COLORS.button,
            color: "#fff",
            padding: "12px 24px",
            borderRadius: 20,
            fontSize: 14,
            fontWeight: 600,
            zIndex: 200,
            whiteSpace: "nowrap",
            animation: "successPop 0.4s ease forwards",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span>✓</span>
          <span>약이 목록에 추가되었습니다.</span>
        </div>
      )}

      {!deleteMode && (
        <div
          style={{
            position: "fixed",
            bottom: 0,
            left: "50%",
            transform: "translateX(-50%)",
            width: "100%",
            maxWidth: 460,
            background: COLORS.cardBg,
            borderTop: `1px solid ${COLORS.border}`,
            padding: "12px 16px",
            display: "flex",
            gap: 8,
            zIndex: 10,
          }}
        >
          <Button variant="secondary" onClick={handleCancel} style={{ flex: 1 }}>
            취소
          </Button>
          <Button
            variant="primary"
            disabled={medicinesDraft.length === 0}
            loading={saving}
            onClick={handleSave}
            style={{ flex: 1 }}
          >
            저장
          </Button>
        </div>
      )}
    </div>
  );
}
