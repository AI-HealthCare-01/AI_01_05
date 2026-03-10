import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchMedicines } from "../api/medicines";
import { Button } from "../components/Button";
import { EmptyState, ErrorMessage, Loading } from "../components/CommonUI";
import { COLORS } from "../constants/theme";
import { useMedicationFlow } from "../store/MedicationFlowContext";
import type { MedicineDraftItem, MedicineSearchItem } from "../types/medicine";

const cardStyle: CSSProperties = {
  background: COLORS.cardBg,
  borderRadius: 20,
  border: `1px solid ${COLORS.border}`,
  padding: 20,
  marginBottom: 16,
};

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function MedicineSearchPage() {
  const navigate = useNavigate();
  const { addDraft } = useMedicationFlow();

  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<MedicineSearchItem[]>([]);
  const [selectedItems, setSelectedItems] = useState<MedicineSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!keyword.trim()) {
      setResults([]);
      setError("");
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const data = await searchMedicines(keyword.trim());
        setResults(data ?? []);
      } catch {
        setError("검색 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [keyword]);

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
      <div style={{ width: "100%", maxWidth: 460, paddingBottom: 100 }}>
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 16,
          }}
        >
          <button
            onClick={() => navigate(-1)}
            style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: COLORS.text }}
          >
            ←
          </button>
          <span style={{ fontWeight: 800, fontSize: 18, color: COLORS.text }}>약 검색</span>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="약 이름을 입력하세요"
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
                padding: "12px 16px",
                cursor: "pointer",
                background: isSelected ? COLORS.selectedCellBg : COLORS.cardBg,
                border: isSelected
                  ? `1px solid ${COLORS.button}`
                  : `1px solid ${COLORS.border}`,
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
                {isSelected && "✓ "}
                {item.item_name}
              </div>
              {item.entp_name && (
                <div style={{ fontSize: 12, color: COLORS.subText, marginTop: 2 }}>
                  {item.entp_name}
                </div>
              )}
            </div>
          );
        })}
      </div>

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
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: 13, color: COLORS.button, fontWeight: 600, flex: 1 }}>
          {selectedItems.length > 0
            ? `${selectedItems.length}개 선택됨`
            : "약을 선택해주세요"}
        </span>
        <Button variant="secondary" onClick={() => navigate(-1)}>
          이전
        </Button>
        <Button variant="primary" disabled={selectedItems.length === 0} onClick={handleNext}>
          다음 →
        </Button>
      </div>
    </div>
  );
}
