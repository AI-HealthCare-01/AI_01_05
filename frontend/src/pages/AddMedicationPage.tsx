import type { CSSProperties } from "react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { parsePrescription } from "../api/medicines";
import { COLORS } from "../constants/theme";
import { useMedicationFlow } from "../store/MedicationFlowContext";
import type { MedicineDraftItem } from "../types/medicine";

const cardStyle: CSSProperties = {
  background: COLORS.cardBg,
  borderRadius: 20,
  border: `1px solid ${COLORS.border}`,
  padding: 20,
  marginBottom: 16,
};

const TODAY = new Date().toISOString().slice(0, 10);
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"];

export default function AddMedicationPage() {
  const navigate = useNavigate();
  const { addDraft } = useMedicationFlow();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type)) {
      showToast("JPG, PNG, HEIC 이미지만 지원합니다.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast("파일 크기는 10MB 이하여야 합니다.");
      return;
    }

    setLoading(true);
    try {
      const result = await parsePrescription(file);

      if (result.items.length === 0) {
        showToast("인식된 약품이 없습니다. 직접 검색해주세요.");
        return;
      }

      const drafts: MedicineDraftItem[] = result.items.map((item) => ({
        item_seq: item.item_seq ?? "",
        item_name: item.item_name,
        start_date: TODAY,
        dose_per_intake: item.dose_per_intake,
        daily_frequency: item.daily_frequency,
        total_days: item.total_days,
        time_slots:
          item.daily_frequency === 1
            ? ["MORNING"]
            : item.daily_frequency === 2
              ? ["MORNING", "EVENING"]
              : item.daily_frequency === 3
                ? ["MORNING", "LUNCH", "EVENING"]
                : ["MORNING"],
      }));

      drafts.forEach(addDraft);
      navigate("/medications/confirm");
    } catch {
      showToast("OCR 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setLoading(false);
      // 같은 파일 재선택 허용
      e.target.value = "";
    }
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
      <div style={{ width: "100%", maxWidth: 460 }}>
        {/* 헤더 */}
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <button
            onClick={() => navigate(-1)}
            style={{
              background: "none",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              color: COLORS.text,
            }}
          >
            ←
          </button>
          <span style={{ fontWeight: 800, fontSize: 18, color: COLORS.text }}>약 추가하기</span>
        </div>

        {/* 사진 등록 카드 */}
        <div
          onClick={() => !loading && fileInputRef.current?.click()}
          aria-busy={loading}
          style={{
            ...cardStyle,
            border: `2px solid ${COLORS.button}`,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <span style={{ fontSize: 32 }}>{loading ? "⏳" : "📷"}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
              {loading ? "약 정보를 인식하는 중입니다..." : "사진으로 간편하게 등록"}
            </div>
            <div style={{ fontSize: 13, color: COLORS.subText, marginTop: 2 }}>
              {loading ? "잠시만 기다려주세요" : "약 봉투나 처방전을 촬영하세요"}
            </div>
          </div>
        </div>

        {/* 숨겨진 파일 입력 */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,image/heif,image/webp"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />

        {/* 직접 검색 카드 */}
        <div
          onClick={() => navigate("/medications/search")}
          style={{
            ...cardStyle,
            border: `1px solid ${COLORS.border}`,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <span style={{ fontSize: 32 }}>🔍</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
              약 이름 직접 검색하기
            </div>
            <div style={{ fontSize: 13, color: COLORS.subText, marginTop: 2 }}>
              약 이름으로 검색하여 등록하세요
            </div>
          </div>
        </div>

        {/* 토스트 */}
        {toast && (
          <div
            style={{
              position: "fixed",
              bottom: 32,
              left: "50%",
              transform: "translateX(-50%)",
              background: "rgba(0,0,0,0.7)",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: 20,
              fontSize: 14,
              zIndex: 200,
              whiteSpace: "nowrap",
            }}
          >
            {toast}
          </div>
        )}
      </div>
    </div>
  );
}
