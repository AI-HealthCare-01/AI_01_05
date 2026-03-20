import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchMedicines } from "../apis/medicines";
import { Button } from "../components/Button";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS } from "../constants/theme";
import { useMedicationFlow } from "../store/MedicationFlowContext";
import type { MedicineDraftItem, MedicineSearchItem } from "../types/medicine";

const LIMIT = 20;

const cardStyle: CSSProperties = {
  background: COLORS.cardBg,
  borderRadius: 20,
  border: `1px solid ${COLORS.border}`,
  padding: 20,
  marginBottom: 5,
};

const fadeSlideUpKeyframes = `
@keyframes checkScale {
  0%   { transform: scale(1); }
  50%  { transform: scale(1.15); }
  100% { transform: scale(1); }
}
@keyframes cardPop {
  0%   { transform: scale(1); }
  50%  { transform: scale(1.05); }
  100% { transform: scale(1); }
}
@keyframes itemFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
`;

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function MedicineSearchPage() {
  const navigate = useNavigate();
  const { addDraft } = useMedicationFlow();

  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<MedicineSearchItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedItems, setSelectedItems] = useState<MedicineSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const totalPages = Math.max(1, Math.ceil(totalCount / LIMIT));

  useEffect(() => {
    if (!keyword.trim()) {
      setResults([]);
      setTotalCount(0);
      setPage(1);
      setError("");
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const data = await searchMedicines(keyword.trim(), LIMIT, (page - 1) * LIMIT);
        setResults(data.items ?? []);
        setTotalCount(data.total_count ?? 0);
      } catch {
        setError("검색 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [keyword, page]);

  const goToPage = (p: number) => {
    if (p < 1 || p > totalPages) return;
    setPage(p);
  };

  const toggleItem = (item: MedicineSearchItem) => {
    setSelectedItems((prev) =>
      prev.some((s) => s.item_seq === item.item_seq)
        ? prev.filter((s) => s.item_seq !== item.item_seq)
        : [...prev, item]
    );
  };

  const handleNext = () => {
    if (selectedItems.length === 0) return;
    selectedItems.forEach((item) => {
      addDraft({
        item_seq: item.item_seq,
        item_name: item.item_name,
        start_date: todayStr(),
        dose_per_intake: 1,
        daily_frequency: 1,
        total_days: 7,
        time_slots: ["MORNING"],
      } satisfies MedicineDraftItem);
    });
    navigate("/medications/confirm");
  };

  const pageButtons = () => {
    const buttons: number[] = [];
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    for (let i = start; i <= end; i++) buttons.push(i);
    return buttons;
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: COLORS.background,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <style>{fadeSlideUpKeyframes}</style>

      {/* Scrollable content area */}
      <div style={{ width: "100%", maxWidth: 460, flex: 1, padding: 16, paddingBottom: 0 }}>
        {/* Title */}
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            marginBottom: 16,
          }}
        >
          <button
            onClick={() => navigate("/main")}
            style={{
              position: "absolute",
              left: 20,
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
          <span style={{ fontWeight: 800, fontSize: 18, color: COLORS.text }}>약 검색</span>
        </div>

        {/* Search input */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <input
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1); }}
            placeholder="약 이름 또는 성분명을 입력하세요"
            aria-busy={loading}
            style={{
              flex: 1,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 12,
              padding: "12px 14px",
              fontSize: 14,
              outline: "none",
            }}
          />
          <Button variant="primary" onClick={() => {}}>
            🔍
          </Button>
        </div>

        {loading && <Loading />}
        {error && <ErrorMessage message={error} />}

        {!loading && !error && keyword && results.length === 0 && (
          <EmptyState message="검색 결과가 없습니다" />
        )}

        {results.map((item) => {
          const isSelected = selectedItems.some((s) => s.item_seq === item.item_seq);
          return (
            <div
              key={item.item_seq}
              onClick={() => toggleItem(item)}
              style={{
                ...cardStyle,
                padding: "10px 16px",
                cursor: "pointer",
                background: isSelected ? COLORS.selectedCellBg : COLORS.cardBg,
                border: isSelected
                  ? `1px solid ${COLORS.button}`
                  : `1px solid ${COLORS.border}`,
                transition: "all 0.2s ease",
                animation: isSelected ? "cardPop 0.25s ease" : undefined,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="checkbox"
                  readOnly
                  checked={isSelected}
                  style={{
                    accentColor: COLORS.button,
                    width: 16,
                    height: 16,
                    cursor: "pointer",
                    flexShrink: 0,
                    animation: isSelected ? "checkScale 0.25s ease" : undefined,
                  }}
                />
                <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
                  {item.item_name}
                </div>
              </div>
              {item.entp_name && (
                <div style={{ fontSize: 12, color: COLORS.subText, marginTop: 2, paddingLeft: 25 }}>
                  {item.entp_name}
                </div>
              )}
            </div>
          );
        })}

        {/* Pagination */}
        {!loading && !error && totalCount > LIMIT && (
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 4, padding: "12px 0" }}>
            <button
              onClick={() => goToPage(page - 1)}
              disabled={page <= 1}
              style={{
                border: "none",
                background: "none",
                cursor: page <= 1 ? "default" : "pointer",
                fontSize: 14,
                color: page <= 1 ? COLORS.border : COLORS.text,
                padding: "4px 8px",
              }}
            >
              ◀
            </button>
            {pageButtons().map((p) => (
              <button
                key={p}
                onClick={() => goToPage(p)}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  border: p === page ? `2px solid ${COLORS.button}` : `1px solid ${COLORS.border}`,
                  background: p === page ? COLORS.button : COLORS.cardBg,
                  color: p === page ? "#fff" : COLORS.text,
                  fontWeight: p === page ? 700 : 400,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => goToPage(page + 1)}
              disabled={page >= totalPages}
              style={{
                border: "none",
                background: "none",
                cursor: page >= totalPages ? "default" : "pointer",
                fontSize: 14,
                color: page >= totalPages ? COLORS.border : COLORS.text,
                padding: "4px 8px",
              }}
            >
              ▶
            </button>
          </div>
        )}
      </div>

      {/* Sticky bottom panel */}
      <div
        style={{
          position: "sticky",
          bottom: 0,
          width: "100%",
          maxWidth: 460,
          background: COLORS.cardBg,
          borderTop: `1px solid ${COLORS.border}`,
          boxShadow: "0 -4px 16px rgba(0,0,0,0.06)",
          padding: "12px 16px",
          transition: "all 0.2s ease",
        }}
      >
        {/* Row 1: count + buttons */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 14, color: COLORS.button, fontWeight: 700 }}>
            {selectedItems.length > 0 ? `${selectedItems.length}개 선택됨` : "약을 선택해주세요"}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <Button variant="secondary" onClick={() => navigate(-1)}>
              이전
            </Button>
            <Button variant="primary" disabled={selectedItems.length === 0} onClick={handleNext}>
              다음 →
            </Button>
          </div>
        </div>

        {/* Row 2: selected medicine list */}
        {selectedItems.length > 0 && (
          <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            {selectedItems.map((item, idx) => (
              <div
                key={item.item_seq}
                style={{
                  fontSize: 13,
                  color: COLORS.text,
                  padding: "4px 0",
                  borderBottom: idx < selectedItems.length - 1 ? `1px solid ${COLORS.border}` : "none",
                  animation: "itemFadeIn 0.2s ease",
                }}
              >
                {item.item_name}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
