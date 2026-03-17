import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  deleteUserMedication,
  getUserMedications,
  type UserMedicationItem,
} from "../api/userMedications";
import { COLORS } from "../constants/theme";

// ── 유틸 ────────────────────────────────────────────────────────────────────

const SLOT_LABEL: Record<string, string> = {
  MORNING: "아침",
  LUNCH: "점심",
  EVENING: "저녁",
  BEDTIME: "취침 전",
};

function formatSlots(slots: string[]): string {
  if (!slots || slots.length === 0) return "-";
  return slots.map((s) => SLOT_LABEL[s] ?? s).join(" · ");
}

// ── 스켈레톤 ────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <style>{`@keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}`}</style>
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          style={{
            height: 96,
            borderRadius: 14,
            background: "linear-gradient(90deg,#ececec 25%,#f5f5f5 50%,#ececec 75%)",
            backgroundSize: "400% 100%",
            animation: "sk 1.4s ease-in-out infinite",
          }}
        />
      ))}
    </div>
  );
}

// ── 삭제 확인 모달 ───────────────────────────────────────────────────────────

interface DeleteModalProps {
  isOpen: boolean;
  isDeleting: boolean;
  itemName: string;
  onConfirm: () => void;
  onClose: () => void;
}

function DeleteConfirmModal({ isOpen, isDeleting, itemName, onConfirm, onClose }: DeleteModalProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !isDeleting) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, isDeleting, onClose]);

  useEffect(() => {
    if (!isOpen || !ref.current) return;
    const els = ref.current.querySelectorAll<HTMLElement>("button");
    const first = els[0];
    const last = els[els.length - 1];
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      }
    };
    document.addEventListener("keydown", trap);
    first?.focus();
    return () => document.removeEventListener("keydown", trap);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget && !isDeleting) onClose(); }}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
      }}
    >
      <div
        ref={ref}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="med-del-title"
        aria-describedby="med-del-desc"
        style={{
          background: "#fff", borderRadius: 16, padding: 24,
          maxWidth: 320, width: "90%", display: "grid", gap: 16,
          boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
        }}
      >
        <h2 id="med-del-title" style={{ margin: 0, fontSize: 18 }}>복용약 삭제</h2>
        <p id="med-del-desc" style={{ margin: 0, fontSize: 14, color: COLORS.text, lineHeight: 1.6 }}>
          <strong>{itemName}</strong>을(를) 삭제하시겠습니까?<br />
          삭제된 복용 기록은 복구할 수 없습니다.
        </p>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onClose}
            disabled={isDeleting}
            style={{
              flex: 1, padding: "12px 0", borderRadius: 10,
              border: `1px solid ${COLORS.border}`, background: "#fff",
              cursor: "pointer", fontWeight: 600, fontSize: 15, fontFamily: "inherit",
            }}
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            aria-busy={isDeleting}
            style={{
              flex: 1, padding: "12px 0", borderRadius: 10, border: "none",
              background: "#fee2e2", color: "#dc2626",
              cursor: isDeleting ? "not-allowed" : "pointer",
              fontWeight: 700, fontSize: 15, fontFamily: "inherit",
              opacity: isDeleting ? 0.65 : 1,
            }}
          >
            {isDeleting ? "삭제 중..." : "삭제"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 약 카드 ──────────────────────────────────────────────────────────────────

interface MedicationCardProps {
  item: UserMedicationItem;
  isDeleting: boolean;
  onDeleteClick: () => void;
}

function MedicationCard({ item, isDeleting, onDeleteClick }: MedicationCardProps) {
  const isActive = item.status === "ACTIVE";

  return (
    <div
      style={{
        borderRadius: 14,
        border: isActive ? `1.5px solid ${COLORS.button}` : `1px solid ${COLORS.border}`,
        background: isActive ? "#f0f5ee" : "#f5f5f5",
        padding: "14px 16px",
        display: "grid",
        gap: 8,
        opacity: isDeleting ? 0.5 : 1,
        transition: "opacity 0.2s ease",
      }}
    >
      {/* 상단: 약 이름 + 상태 뱃지 */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
        <span
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: isActive ? COLORS.text : "#999",
            lineHeight: 1.4,
            flex: 1,
            minWidth: 0,
          }}
        >
          {item.item_name}
        </span>
        <span
          style={{
            flexShrink: 0,
            fontSize: 11,
            fontWeight: 700,
            padding: "3px 8px",
            borderRadius: 999,
            background: isActive ? COLORS.button : "#ddd",
            color: isActive ? "#fff" : "#888",
          }}
        >
          {isActive ? "복용 중" : "중단"}
        </span>
      </div>

      {/* 복용 정보 */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px" }}>
        <span style={{ fontSize: 13, color: isActive ? "#5a7a4a" : "#aaa" }}>
          1회 {item.dose_per_intake}정 · 하루 {item.daily_frequency}회
        </span>
        <span style={{ fontSize: 13, color: isActive ? "#5a7a4a" : "#aaa" }}>
          {formatSlots(item.time_slots)}
        </span>
      </div>

      {/* 시작일 + 삭제 버튼 */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: "#aaa" }}>
          시작일 {item.start_date?.slice(0, 10) ?? "-"}
        </span>
        <button
          type="button"
          onClick={onDeleteClick}
          disabled={isDeleting}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            color: "#dc2626",
            fontSize: 13,
            textDecoration: "underline",
            cursor: isDeleting ? "not-allowed" : "pointer",
            fontFamily: "inherit",
          }}
        >
          삭제
        </button>
      </div>
    </div>
  );
}

// ── MedicationManagePage ─────────────────────────────────────────────────────

export default function MedicationManagePage() {
  const navigate = useNavigate();

  const [items, setItems] = useState<UserMedicationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 삭제 모달 상태
  const [deleteTarget, setDeleteTarget] = useState<UserMedicationItem | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // ── 목록 조회 ──
  const fetchList = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await getUserMedications();
      setItems(res?.items ?? []);
    } catch {
      setError("복용약 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void fetchList(); }, []);

  // ── ACTIVE 먼저 정렬 ──
  const sortedItems = [...items].sort((a, b) => {
    if (a.status === "ACTIVE" && b.status !== "ACTIVE") return -1;
    if (a.status !== "ACTIVE" && b.status === "ACTIVE") return 1;
    return 0;
  });

  // ── 삭제 처리 (optimistic update) ──
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    const targetId = deleteTarget.medication_id;

    // optimistic: 즉시 목록에서 제거
    setItems((prev) => prev.filter((i) => i.medication_id !== targetId));
    setDeleteTarget(null);
    setDeletingId(targetId);

    try {
      await deleteUserMedication(targetId);
    } catch {
      // 실패 시 롤백 후 재조회
      setError("삭제에 실패했습니다. 다시 시도해주세요.");
      await fetchList();
    } finally {
      setDeletingId(null);
    }
  };

  const activeCount = items.filter((i) => i.status === "ACTIVE").length;

  return (
    <main
      style={{
        background: COLORS.background,
        minHeight: "100vh",
        padding: 16,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div style={{ width: "100%", maxWidth: 460, display: "grid", gap: 12, alignContent: "start" }}>

        {/* 헤더 */}
        <button
          onClick={() => navigate("/mypage")}
          style={{
            background: "none", border: "none", cursor: "pointer", fontSize: 15,
            color: COLORS.subText, fontWeight: 600, padding: "16px 0",
            display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit",
          }}
        >
          ‹ 뒤로
        </button>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>복용약 관리</h1>
          <button
            type="button"
            onClick={() => navigate("/medications/add")}
            style={{
              background: COLORS.buttonBg, color: "#fff", border: "none",
              borderRadius: 10, padding: "8px 14px", fontWeight: 600,
              cursor: "pointer", fontSize: 13, fontFamily: "inherit",
            }}
          >
            + 약 추가
          </button>
        </div>

        {/* 복용 중 약 개수 요약 */}
        {!isLoading && !error && (
          <p style={{ margin: 0, fontSize: 13, color: COLORS.subText }}>
            현재 복용 중인 약{" "}
            <strong style={{ color: COLORS.button }}>{activeCount}개</strong>
          </p>
        )}

        {/* 에러 */}
        {error && (
          <div
            style={{
              background: "#fff0f0", border: "1px solid #fca5a5",
              borderRadius: 10, padding: "12px 16px",
              display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
            }}
          >
            <span style={{ fontSize: 14, color: "#dc2626" }}>{error}</span>
            <button
              onClick={() => void fetchList()}
              style={{
                background: "none", border: "none", color: "#dc2626",
                fontSize: 13, textDecoration: "underline", cursor: "pointer",
                fontFamily: "inherit", flexShrink: 0,
              }}
            >
              다시 시도
            </button>
          </div>
        )}

        {/* 로딩 */}
        {isLoading && <Skeleton />}

        {/* 빈 상태 */}
        {!isLoading && !error && sortedItems.length === 0 && (
          <div
            style={{
              background: "#fff", borderRadius: 14, border: `1px solid ${COLORS.border}`,
              padding: "40px 20px", textAlign: "center",
            }}
          >
            <p style={{ margin: "0 0 4px", fontSize: 32 }}>💊</p>
            <p style={{ margin: "0 0 12px", fontSize: 15, color: COLORS.text, fontWeight: 600 }}>
              등록된 약이 없습니다
            </p>
            <p style={{ margin: "0 0 20px", fontSize: 13, color: COLORS.subText }}>
              약 봉투를 촬영하거나 직접 검색해서 추가해보세요.
            </p>
            <button
              onClick={() => navigate("/medications/add")}
              style={{
                background: COLORS.buttonBg, color: "#fff", border: "none",
                borderRadius: 10, padding: "10px 20px", fontWeight: 600,
                cursor: "pointer", fontSize: 14, fontFamily: "inherit",
              }}
            >
              약 추가하기
            </button>
          </div>
        )}

        {/* 약 목록 */}
        {!isLoading && sortedItems.length > 0 && (
          <div style={{ display: "grid", gap: 10 }}>
            {sortedItems.map((item) => (
              <MedicationCard
                key={item.medication_id}
                item={item}
                isDeleting={deletingId === item.medication_id}
                onDeleteClick={() => setDeleteTarget(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 삭제 확인 모달 */}
      <DeleteConfirmModal
        isOpen={deleteTarget !== null}
        isDeleting={deletingId === deleteTarget?.medication_id}
        itemName={deleteTarget?.item_name ?? ""}
        onConfirm={() => void handleDeleteConfirm()}
        onClose={() => { if (!deletingId) setDeleteTarget(null); }}
      />
    </main>
  );
}
