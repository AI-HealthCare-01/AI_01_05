import type { CSSProperties } from "react";
import { useRef, useState } from "react";
import ocrSample from "../assets/images/ocr_sample/ocr_sample.png";
import { useNavigate } from "react-router-dom";
import { parsePrescription } from "../api/medicines";
import { COLORS } from "../constants/theme";
import { useMedicationFlow } from "../store/MedicationFlowContext";
import type { MedicineDraftItem } from "../types/medicine";

const ocrLoadingKeyframes = `
@keyframes ocrPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); }
}
@keyframes ocrProgress {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
`;

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

  // 카메라 촬영용 (capture="environment")
  const cameraInputRef = useRef<HTMLInputElement>(null);
  // 갤러리 업로드용
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [showSourceSheet, setShowSourceSheet] = useState(false);
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
            justifyContent: "center",
            position: "relative",
            marginBottom: 24,
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
              transition: "all 0.2s ease",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </button>
          <span style={{ fontWeight: 800, fontSize: 18, color: COLORS.text }}>약 추가하기</span>
        </div>

        {/* 촬영 가이드 카드 */}
        <div style={{ ...cardStyle, padding: 0, overflow: "hidden", marginBottom: 12 }}>
          <div
            style={{
              background: "#f5f5f5",
              padding: "6px 20px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <img
              src={ocrSample}
              alt="약 봉투 촬영 예시"
              style={{ width: "100%", maxWidth: 380, borderRadius: 8, display: "block" }}
            />
          </div>
          <div style={{ padding: "14px 18px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
              <span style={{ fontSize: 23 }}>📸</span>
              <span style={{ fontWeight: 700, fontSize: 17, color: COLORS.text }}>약 봉투 촬영 가이드</span>
              <span
                style={{
                  marginLeft: "auto",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#99A988",
                  background: "#e8f0e4",
                  padding: "2px 8px",
                  borderRadius: 20,
                }}
              >
                정확도 UP ↑
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {([
                ["∙", "평평하게 펼치기", "구겨지거나 접히지 않게 펼쳐주세요"],
                ["∙", "밝은 곳에서 촬영", "빛 반사·그림자 없는 밝은 환경에서 찍어주세요"],
                ["∙", "화면에 꽉 차게", "처방 내역과 약 이름이 모두 들어오게 맞춰주세요"],
                ["∙", "초점 맞추기", "카메라가 흔들리지 않게 주의해 주세요"],
              ] as [string, string, string][]).map(([icon, title, desc]) => (
                <div key={title} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                  <span style={{ fontSize: 20, lineHeight: "18px", flexShrink: 0 }}>{icon}</span>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "baseline" }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: COLORS.text, whiteSpace: "nowrap" }}>{title}</span>
                    <span style={{ fontSize: 13, color: COLORS.subText, lineHeight: "16px" }}>{desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 사진 등록 카드 */}
        <div
          onClick={() => !loading && setShowSourceSheet(true)}
          aria-busy={loading}
          style={{
            ...cardStyle,
            border: `2px solid ${COLORS.button}`,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
            display: "flex",
            alignItems: "center",
            gap: 16,
            transition: "all 0.2s ease",
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.transform = "translateY(-2px)";
            el.style.boxShadow = `0 8px 24px rgba(99,153,80,0.18), 0 2px 8px rgba(99,153,80,0.10)`;
            el.style.borderColor = COLORS.button;
            const icon = el.querySelector(".btn-icon") as HTMLElement | null;
            if (icon) icon.style.transform = "scale(1.05)";
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.transform = "translateY(0)";
            el.style.boxShadow = "none";
            el.style.borderColor = COLORS.button;
            const icon = el.querySelector(".btn-icon") as HTMLElement | null;
            if (icon) icon.style.transform = "scale(1)";
          }}
          onMouseDown={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "scale(0.97)"; }}
          onMouseUp={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)"; }}
        >
          <span className="btn-icon" style={{ fontSize: 32, display: "inline-block", transition: "transform 0.2s ease" }}>
            {loading ? "⏳" : "📷"}
          </span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
              {loading ? "약 정보를 인식하는 중입니다..." : "사진으로 간편하게 등록"}
            </div>
            <div style={{ fontSize: 13, color: COLORS.subText, marginTop: 2 }}>
              {loading ? "잠시만 기다려주세요" : "약 봉투를 촬영하여 등록하세요"}
            </div>
          </div>
        </div>

        {/* 카메라 촬영용 input */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/jpeg,image/png,image/heic,image/heif,image/webp"
          capture="environment"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
        {/* 갤러리 업로드용 input */}
        <input
          ref={galleryInputRef}
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
            border: `2px solid ${COLORS.button}`,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 16,
            transition: "all 0.2s ease",
          }}
          onMouseEnter={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.transform = "translateY(-2px)";
            el.style.boxShadow = `0 8px 24px rgba(99,153,80,0.12), 0 2px 8px rgba(99,153,80,0.08)`;
            el.style.borderColor = COLORS.button;
            const icon = el.querySelector(".btn-icon") as HTMLElement | null;
            if (icon) icon.style.transform = "scale(1.05)";
          }}
          onMouseLeave={(e) => {
            const el = e.currentTarget as HTMLDivElement;
            el.style.transform = "translateY(0)";
            el.style.boxShadow = "none";
            el.style.borderColor = COLORS.button;
            const icon = el.querySelector(".btn-icon") as HTMLElement | null;
            if (icon) icon.style.transform = "scale(1)";
          }}
          onMouseDown={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "scale(0.97)"; }}
          onMouseUp={(e) => { (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)"; }}
        >
          <span className="btn-icon" style={{ fontSize: 32, display: "inline-block", transition: "transform 0.2s ease" }}>🔍</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
              약 이름 직접 검색하기
            </div>
            <div style={{ fontSize: 13, color: COLORS.subText, marginTop: 2 }}>
              약 이름으로 검색하여 등록하세요
            </div>
          </div>
        </div>
      </div>

      {/* 촬영/업로드 선택 바텀시트 */}
      {showSourceSheet && (
        <>
          {/* 딤 배경 */}
          <div
            onClick={() => setShowSourceSheet(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.4)",
              zIndex: 100,
            }}
          />
          {/* 시트 */}
          <div
            style={{
              position: "fixed",
              bottom: 0,
              left: "50%",
              transform: "translateX(-50%)",
              width: "100%",
              maxWidth: 460,
              background: COLORS.cardBg,
              borderRadius: "20px 20px 0 0",
              padding: "20px 16px 32px",
              zIndex: 101,
            }}
          >
            <div
              style={{
                width: 40,
                height: 4,
                background: COLORS.border,
                borderRadius: 2,
                margin: "0 auto 20px",
              }}
            />
            <div style={{ fontWeight: 700, fontSize: 16, color: COLORS.text, marginBottom: 16, textAlign: "center" }}>
              사진 등록 방법 선택
            </div>

            {/* 카메라 촬영 */}
            <button
              onClick={() => {
                setShowSourceSheet(false);
                cameraInputRef.current?.click();
              }}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "14px 16px",
                background: COLORS.selectedCellBg,
                border: `2px solid ${COLORS.button}`,
                borderRadius: 14,
                cursor: "pointer",
                marginBottom: 10,
              }}
            >
              <span style={{ fontSize: 24 }}>📷</span>
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>카메라로 촬영</div>
                <div style={{ fontSize: 12, color: COLORS.subText, marginTop: 2 }}>지금 바로 약 봉투를 촬영합니다 (모바일)</div>
              </div>
            </button>

            {/* 갤러리 업로드 */}
            <button
              onClick={() => {
                setShowSourceSheet(false);
                galleryInputRef.current?.click();
              }}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "14px 16px",
                background: COLORS.cardBg,
                border: `2px solid ${COLORS.button}`,
                borderRadius: 14,
                cursor: "pointer",
                marginBottom: 10,
              }}
            >
              <span style={{ fontSize: 24 }}>🖼️</span>
              <div style={{ textAlign: "left" }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>갤러리에서 선택</div>
                <div style={{ fontSize: 12, color: COLORS.subText, marginTop: 2 }}>저장된 사진을 불러옵니다</div>
              </div>
            </button>

            {/* 취소 */}
            <button
              onClick={() => setShowSourceSheet(false)}
              style={{
                width: "100%",
                padding: "14px",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 15,
                color: COLORS.subText,
                marginTop: 4,
              }}
            >
              취소
            </button>
          </div>
        </>
      )}

      {/* OCR 로딩 모달 오버레이 */}
      {loading && (
        <>
          <style>{ocrLoadingKeyframes}</style>
          <div
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.5)",
              zIndex: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                background: COLORS.cardBg,
                borderRadius: 24,
                padding: "40px 32px",
                width: "85%",
                maxWidth: 320,
                textAlign: "center",
                boxShadow: "0 20px 60px rgba(0,0,0,0.15)",
              }}
            >
              <div style={{ fontSize: 48, animation: "ocrPulse 1.5s ease-in-out infinite", marginBottom: 20 }}>💊</div>
              <div style={{ fontWeight: 700, fontSize: 18, color: COLORS.text, marginBottom: 16 }}>
                약 정보를 인식하는 중입니다...
              </div>
              <div
                style={{
                  width: "100%",
                  height: 4,
                  background: COLORS.border,
                  borderRadius: 2,
                  overflow: "hidden",
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    width: "40%",
                    height: "100%",
                    background: COLORS.button,
                    borderRadius: 2,
                    animation: "ocrProgress 1.2s ease-in-out infinite",
                  }}
                />
              </div>
              <div style={{ fontSize: 14, color: COLORS.subText, lineHeight: 1.5 }}>
                약 봉투를 분석하고 있어요.<br />잠시만 기다려주세요.
              </div>
            </div>
          </div>
        </>
      )}

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
  );
}
