import type { CSSProperties } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { COLORS } from "../constants/theme";

const cardStyle: CSSProperties = {
  background: COLORS.cardBg,
  borderRadius: 20,
  border: `1px solid ${COLORS.border}`,
  padding: 20,
  marginBottom: 16,
};

export default function AddMedicationPage() {
  const navigate = useNavigate();
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2000);
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

        <div
          onClick={() => showToast("준비 중입니다")}
          aria-disabled="true"
          style={{
            ...cardStyle,
            opacity: 0.5,
            cursor: "not-allowed",
            display: "flex",
            alignItems: "center",
            gap: 16,
            position: "relative",
          }}
        >
          <span style={{ fontSize: 32 }}>📷</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: COLORS.text }}>
              사진으로 간편하게 등록
            </div>
            <div style={{ fontSize: 13, color: COLORS.subText, marginTop: 2 }}>
              약 봉투나 처방전을 촬영하세요
            </div>
          </div>
          <span
            style={{
              position: "absolute",
              top: 12,
              right: 12,
              background: "#E0E0E0",
              borderRadius: 20,
              padding: "2px 8px",
              fontSize: 11,
              color: COLORS.subText,
            }}
          >
            준비 중
          </span>
        </div>

        <div
          onClick={() => navigate("/medications/search")}
          style={{
            ...cardStyle,
            border: `2px solid ${COLORS.button}`,
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
            }}
          >
            {toast}
          </div>
        )}
      </div>
    </div>
  );
}
