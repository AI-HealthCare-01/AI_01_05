import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteMyAccount, getMyInfo, updateMyInfo } from "../apis/users";
import { updateTimeSlots } from "../apis/userMedications";
import { getMyCharacter } from "../apis/characterApi";
import { CHARACTER_IMAGE_BY_ID, DEFAULT_CHARACTER_IMAGE } from "../constants/characters";
import { COLORS } from "../constants/theme";
import { useAuthStore } from "../store/authStore";
import type { UserMe } from "../types";
import {
  DEFAULT_TIME_RANGES,
  isValidTimeString,
  loadTimeRanges,
  saveTimeRanges,
  type TimeRange,
} from "../utils/timeRange";

// ─── 시간대 설정 섹션 ────────────────────────────────────────────────────────

function TimeRangeSettings() {
  const [ranges, setRanges] = useState<TimeRange[]>(() => loadTimeRanges());
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [saved, setSaved] = useState(false);

  const validate = (next: TimeRange[]): Record<number, string> => {
    const errs: Record<number, string> = {};
    next.forEach((r, i) => {
      if (!isValidTimeString(r.start)) errs[i] = `시작 시간 형식이 올바르지 않습니다 (HH:MM)`;
      else if (!isValidTimeString(r.end)) errs[i] = `종료 시간 형식이 올바르지 않습니다 (HH:MM)`;
    });
    return errs;
  };

  const handleChange = (index: number, field: "start" | "end", value: string) => {
    setRanges((prev) => prev.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
    setErrors((prev) => { const next = { ...prev }; delete next[index]; return next; });
    setSaved(false);
  };

  const handleSave = async () => {
    const errs = validate(ranges);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    // 1. 로컬 저장 (항상 성공)
    saveTimeRanges(ranges);

    // 2. DB 저장 (silent fail - 실패해도 로컬 저장은 유지)
    try {
      // 각 슬롯의 start 시간을 DB에 저장
      const slotMap: Record<string, string> = {};
      for (const r of ranges) {
        slotMap[r.slot] = r.start;
      }
      await updateTimeSlots({
        morning: slotMap.morning,
        lunch: slotMap.lunch,
        evening: slotMap.evening,
        bedtime: slotMap.bedtime,
      });
    } catch {
      // API 실패해도 무시 (로컬 저장은 성공)
      console.warn("시간대 DB 저장 실패 (로컬 저장은 완료됨)");
    }

    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const handleReset = () => {
    setRanges(DEFAULT_TIME_RANGES);
    setErrors({});
    setSaved(false);
  };

  const inputStyle: React.CSSProperties = {
    width: 120, padding: "6px 8px", borderRadius: 6, border: `1px solid ${COLORS.border}`,
    fontSize: 14, textAlign: "center", fontFamily: "inherit",
  };

  return (
    <section
      style={{
        background: "#fff", borderRadius: 16, padding: 20,
        border: `1px solid ${COLORS.border}`, display: "grid", gap: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <p style={{ margin: 0, fontWeight: 700, fontSize: 15, color: COLORS.subText }}>복약 시간대 설정</p>
        <button
          type="button"
          onClick={handleReset}
          style={{
            background: "none", border: `1px solid ${COLORS.border}`, borderRadius: 8,
            padding: "4px 10px", fontSize: 12, color: COLORS.subText, cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          기본값 복원
        </button>
      </div>

      <p style={{ margin: 0, fontSize: 12, color: COLORS.subText, lineHeight: 1.6 }}>
        메인 화면의 &quot;오늘의 ○○ 기분&quot;, &quot;오늘의 ○○ 약&quot; 설정에 따라 자동 변경 됩니다.
      </p>

      {ranges.map((range, i) => (
        <div key={range.slot}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ width: 52, fontSize: 14, fontWeight: 600, color: COLORS.text, flexShrink: 0 }}>
              {range.label}
            </span>
            <input
              type="time"
              value={range.start}
              onChange={(e) => handleChange(i, "start", e.target.value)}
              style={{ ...inputStyle, borderColor: errors[i] ? COLORS.error : COLORS.border }}
              aria-label={`${range.label} 시작 시간`}
            />
            <span style={{ fontSize: 13, color: COLORS.subText }}>~</span>
            <input
              type="time"
              value={range.end}
              onChange={(e) => handleChange(i, "end", e.target.value)}
              style={{ ...inputStyle, borderColor: errors[i] ? COLORS.error : COLORS.border }}
              aria-label={`${range.label} 종료 시간`}
            />
          </div>
          {errors[i] && (
            <p style={{ margin: "4px 0 0 62px", fontSize: 12, color: COLORS.error }}>{errors[i]}</p>
          )}
        </div>
      ))}

      {saved && (
        <p style={{ margin: 0, fontSize: 13, color: "#16a34a" }}>✓ 시간대 설정이 저장되었습니다.</p>
      )}

      <button
        type="button"
        onClick={handleSave}
        style={{
          padding: "12px 0", borderRadius: 12, border: "none",
          background: COLORS.buttonBg, color: "#fff",
          fontWeight: 700, fontSize: 15, cursor: "pointer", fontFamily: "inherit",
        }}
      >
        시간대 저장
      </button>
    </section>
  );
}

// ─── 유효성 검사 ────────────────────────────────────────────────────────────

type FormFields = { nickname: string; email: string | null; birthday: string | null };
type FieldErrors = Partial<Record<keyof FormFields, string>>;
type ProfileFormValues = FormFields & {
  gender: UserMe["gender"];
  marketing_agreed: boolean;
  sms_agreed: boolean;
};

function validateField(field: keyof FormFields, value: string | null): string | null {
  switch (field) {
    case "nickname":
      if (!value || value.trim().length === 0) return "닉네임을 입력해주세요.";
      if (value.length > 10) return "닉네임은 10자 이하여야 합니다.";
      return null;
    case "email":
      if (!value || value.trim() === "") return null;
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "올바른 이메일 형식이 아닙니다.";
      return null;
    case "birthday": {
      if (!value || value.trim() === "") return null;
      const birth = new Date(value);
      const limit = new Date();
      limit.setFullYear(limit.getFullYear() - 14);
      if (isNaN(birth.getTime())) return "올바른 날짜 형식이 아닙니다.";
      if (birth > limit) return "만 14세 이상만 사용 가능합니다.";
      return null;
    }
    default:
      return null;
  }
}

function validateAll(form: FormFields): FieldErrors {
  const errors: FieldErrors = {};
  (["nickname", "email", "birthday"] as const).forEach((f) => {
    const err = validateField(f, form[f]);
    if (err) errors[f] = err;
  });
  return errors;
}

// ─── 에러 파싱 ───────────────────────────────────────────────────────────────

function parseApiError(e: unknown): string {
  const err = e as { detail?: string | Array<{ msg: string }> };
  if (Array.isArray(err.detail)) return err.detail.map((d) => d.msg).join(", ");
  return (err.detail as string) ?? (e instanceof Error ? e.message : "오류가 발생했습니다.");
}

// ─── 스켈레톤 ────────────────────────────────────────────────────────────────

function MyPageSkeleton() {
  const skBase: React.CSSProperties = {
    background: "linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.4s infinite",
    borderRadius: 8,
  };
  return (
    <div aria-busy="true" aria-label="프로필 불러오는 중" style={{ display: "grid", gap: 12 }}>
      <style>{`@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}`}</style>
      <div style={{ ...skBase, height: 80, borderRadius: 16 }} />
      <div style={{ ...skBase, height: 20, width: "40%" }} />
      <div style={{ ...skBase, height: 44 }} />
      <div style={{ ...skBase, height: 20, width: "30%" }} />
      <div style={{ ...skBase, height: 44 }} />
      <div style={{ ...skBase, height: 44 }} />
      <div style={{ ...skBase, height: 44 }} />
      <div style={{ ...skBase, height: 48, borderRadius: 12 }} />
    </div>
  );
}

// ─── 탈퇴 확인 모달 ──────────────────────────────────────────────────────────

interface DeleteConfirmModalProps {
  isOpen: boolean;
  isDeleting: boolean;
  error: string | null;
  onConfirm: () => void;
  onClose: () => void;
}

function DeleteConfirmModal({ isOpen, isDeleting, error, onConfirm, onClose }: DeleteConfirmModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isDeleting, onClose]);

  useEffect(() => {
    if (!isOpen || !modalRef.current) return;
    const focusable = modalRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const trap = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", trap);
    return () => document.removeEventListener("keydown", trap);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !isDeleting) onClose(); }}
    >
      <div
        ref={modalRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        aria-describedby="delete-modal-desc"
        style={{
          background: "#fff", borderRadius: 16, padding: 24, maxWidth: 320, width: "90%",
          display: "grid", gap: 16,
        }}
      >
        <h2 id="delete-modal-title" style={{ margin: 0, fontSize: 18 }}>⚠️ 계정을 삭제할까요?</h2>
        <div id="delete-modal-desc" style={{ fontSize: 14, color: COLORS.text, lineHeight: 1.6 }}>
          <p style={{ margin: "0 0 8px" }}>탈퇴하면 아래 데이터가 영구적으로 삭제됩니다:</p>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>프로필 및 계정 정보</li>
            <li>복용 약 기록</li>
            <li>친구 캐릭터</li>
          </ul>
          <p style={{ margin: "8px 0 0", fontWeight: 600 }}>삭제된 데이터는 복구할 수 없습니다.</p>
        </div>
        {error && <p role="alert" style={{ margin: 0, color: COLORS.error, fontSize: 13 }}>{error}</p>}
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onClose}
            disabled={isDeleting}
            autoFocus
            style={{
              flex: 1, padding: "12px 0", borderRadius: 10, border: `1px solid ${COLORS.border}`,
              background: "#fff", cursor: "pointer", fontWeight: 600, fontFamily: "inherit",
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
              background: "#fee2e2", color: "#dc2626", cursor: "pointer", fontWeight: 700,
              fontFamily: "inherit",
            }}
          >
            {isDeleting ? "탈퇴 처리 중..." : "탈퇴하기"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── MyPage ──────────────────────────────────────────────────────────────────

export function MyPage() {
  const navigate = useNavigate();
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const [userInfo, setUserInfo] = useState<UserMe | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [formValues, setFormValues] = useState<ProfileFormValues>({
    nickname: "",
    email: null,
    birthday: null,
    gender: "UNKNOWN",
    marketing_agreed: false,
    sms_agreed: false,
  });
  const [initialValues, setInitialValues] = useState(formValues);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [characterId, setCharacterId] = useState<number | null>(null);
  const [characterName, setCharacterName] = useState<string>("");

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const isDirty =
    formValues.nickname !== initialValues.nickname ||
    formValues.email !== initialValues.email ||
    formValues.birthday !== initialValues.birthday ||
    formValues.gender !== initialValues.gender ||
    formValues.marketing_agreed !== initialValues.marketing_agreed ||
    formValues.sms_agreed !== initialValues.sms_agreed;

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);
        const [me, char] = await Promise.allSettled([getMyInfo(), getMyCharacter()]);
        if (me.status === "fulfilled" && me.value) {
          const u = me.value;
          setUserInfo(u);
          const vals = {
            nickname: u.nickname,
            email: u.email,
            birthday: u.birthday,
            gender: u.gender,
            marketing_agreed: u.marketing_agreed,
            sms_agreed: u.sms_agreed,
          };
          setFormValues(vals);
          setInitialValues(vals);
        } else {
          setLoadError("내 정보를 불러오지 못했습니다.");
        }
        if (char.status === "fulfilled" && char.value) {
          setCharacterId(char.value.character_id);
          setCharacterName(char.value.name);
        }
      } finally {
        setIsLoading(false);
      }
    };
    void load();
  }, []);

  const handleBlur = (field: keyof FormFields) => {
    const err = validateField(field, formValues[field]);
    setFieldErrors((prev) => ({ ...prev, [field]: err ?? undefined }));
  };

  const handleSubmit = async () => {
    const errors = validateAll(formValues);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setSubmitError(null);
    setSubmitSuccess(false);
    setIsSubmitting(true);
    try {
      const updated = await updateMyInfo({
        nickname: formValues.nickname,
        email: formValues.email || null,
        birthday: formValues.birthday || null,
        gender: formValues.gender,
        marketing_agreed: formValues.marketing_agreed,
        sms_agreed: formValues.sms_agreed,
      });
      setUserInfo(updated);
      setInitialValues(formValues);
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);
    } catch (e) {
      setSubmitError(parseApiError(e));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await deleteMyAccount();
      clearAuth();
      navigate("/login", { replace: true });
    } catch (e) {
      setDeleteError(parseApiError(e));
      setIsDeleting(false);
    }
  };

  const charImage = characterId ? (CHARACTER_IMAGE_BY_ID[characterId] ?? DEFAULT_CHARACTER_IMAGE) : null;

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: `1px solid ${COLORS.border}`, fontSize: 15, boxSizing: "border-box",
    fontFamily: "inherit",
  };
  const labelStyle: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: COLORS.subText, marginBottom: 4 };
  const fieldWrapStyle: React.CSSProperties = { display: "grid", gap: 4 };

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "flex", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: 460, display: "grid", gap: 12, alignContent: "start" }}>
      <button
        onClick={() => navigate("/main")}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          color: COLORS.text,
          display: "flex",
          alignItems: "center",
          padding: "16px 0",
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
      <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>마이페이지</h1>

      {isLoading ? (
        <MyPageSkeleton />
      ) : loadError ? (
        <p style={{ color: COLORS.error }}>{loadError}</p>
      ) : (
        <>
          {/* 캐릭터 카드 */}
          <div
            style={{
              background: "#fff", borderRadius: 16, padding: "16px 20px",
              display: "flex", alignItems: "center", gap: 16,
              border: `1px solid ${COLORS.border}`,
            }}
          >
            {charImage ? (
              <img src={charImage} alt={`${characterName} 캐릭터`} style={{ width: 64, height: 64, objectFit: "contain" }} />
            ) : (
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: COLORS.background }} />
            )}
            <div style={{ flex: 1 }}>
              <p style={{ margin: 0, fontWeight: 700, fontSize: 16 }}>{characterName || "캐릭터 미선택"}</p>
              <p style={{ margin: "2px 0 0", fontSize: 13, color: COLORS.subText }}>나의 친구</p>
            </div>
            <button
              onClick={() => navigate("/character-select", { state: { from: "mypage" } })}
              style={{
                background: COLORS.buttonBg, color: "#fff", border: "none",
                borderRadius: 10, padding: "8px 14px", fontWeight: 600,
                cursor: "pointer", fontSize: 13, fontFamily: "inherit",
              }}
            >
              친구 변경
            </button>
          </div>

          {/* 복용약 관리 버튼 */}
          <button
            type="button"
            onClick={() => navigate("/medications")}
            style={{
              width: "100%",
              background: "#fff",
              border: `1px solid ${COLORS.border}`,
              borderRadius: 16,
              padding: "16px 20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>💊</span>
              <div style={{ textAlign: "left" }}>
                <p style={{ margin: 0, fontWeight: 700, fontSize: 15, color: COLORS.text }}>복용약 관리</p>
                <p style={{ margin: "2px 0 0", fontSize: 13, color: COLORS.subText }}>등록된 약 목록 확인 및 삭제</p>
              </div>
            </div>
            <span style={{ fontSize: 18, color: COLORS.subText }}>›</span>
          </button>

          {/* 프로필 폼 */}
          <section
            style={{
              background: "#fff", borderRadius: 16, padding: 20,
              border: `1px solid ${COLORS.border}`, display: "grid", gap: 16,
            }}
          >
            <p style={{ margin: 0, fontWeight: 700, fontSize: 15, color: COLORS.subText }}>프로필 정보</p>

            <div style={fieldWrapStyle}>
              <label htmlFor="nickname" style={labelStyle}>닉네임 *</label>
              <input
                id="nickname"
                value={formValues.nickname}
                onChange={(e) => setFormValues((p) => ({ ...p, nickname: e.target.value }))}
                onBlur={() => handleBlur("nickname")}
                placeholder="닉네임"
                style={{ ...inputStyle, borderColor: fieldErrors.nickname ? COLORS.error : COLORS.border }}
              />
              {fieldErrors.nickname && <span style={{ fontSize: 12, color: COLORS.error }}>{fieldErrors.nickname}</span>}
            </div>

            <div style={fieldWrapStyle}>
              <label htmlFor="email" style={labelStyle}>이메일</label>
              <input
                id="email"
                type="email"
                value={formValues.email ?? ""}
                onChange={(e) => setFormValues((p) => ({ ...p, email: e.target.value || null }))}
                onBlur={() => handleBlur("email")}
                placeholder="이메일 (선택)"
                style={{ ...inputStyle, borderColor: fieldErrors.email ? COLORS.error : COLORS.border }}
              />
              {fieldErrors.email && <span style={{ fontSize: 12, color: COLORS.error }}>{fieldErrors.email}</span>}
            </div>

            <div style={fieldWrapStyle}>
              <span style={labelStyle}>성별</span>
              <div style={{ display: "flex", gap: 8 }}>
                {(["MALE", "FEMALE", "UNKNOWN"] as const).map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setFormValues((p) => ({ ...p, gender: g }))}
                    style={{
                      flex: 1, padding: "10px 0", borderRadius: 8, fontFamily: "inherit",
                      border: `1px solid ${formValues.gender === g ? COLORS.buttonBg : COLORS.border}`,
                      background: formValues.gender === g ? COLORS.buttonBg : "#fff",
                      color: formValues.gender === g ? "#fff" : COLORS.text,
                      fontWeight: 600, cursor: "pointer", fontSize: 13,
                    }}
                  >
                    {g === "MALE" ? "남성" : g === "FEMALE" ? "여성" : "미선택"}
                  </button>
                ))}
              </div>
            </div>

            <div style={fieldWrapStyle}>
              <label htmlFor="birthday" style={labelStyle}>생년월일</label>
              <input
                id="birthday"
                type="date"
                value={formValues.birthday ?? ""}
                max={(() => { const d = new Date(); d.setFullYear(d.getFullYear() - 14); return d.toISOString().split("T")[0]; })()}
                onChange={(e) => setFormValues((p) => ({ ...p, birthday: e.target.value || null }))}
                onBlur={() => handleBlur("birthday")}
                style={{ ...inputStyle, borderColor: fieldErrors.birthday ? COLORS.error : COLORS.border }}
              />
              {fieldErrors.birthday && <span style={{ fontSize: 12, color: COLORS.error }}>{fieldErrors.birthday}</span>}
            </div>

            <div style={fieldWrapStyle}>
              <span style={labelStyle}>이벤트 및 마케팅 수신 동의 (선택)</span>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  borderRadius: 10,
                  border: `1px solid ${COLORS.border}`,
                  background: "#fff",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, color: COLORS.text }}>상태</span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: formValues.marketing_agreed ? "#166534" : COLORS.subText,
                      background: formValues.marketing_agreed ? "#dcfce7" : "#f3f4f6",
                      borderRadius: 999,
                      padding: "4px 8px",
                    }}
                  >
                    {formValues.marketing_agreed ? "동의" : "미동의"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setFormValues((p) => ({ ...p, marketing_agreed: !p.marketing_agreed }))
                  }
                  aria-pressed={formValues.marketing_agreed}
                  aria-label="이벤트 및 마케팅 수신 동의"
                  style={{
                    width: 46,
                    height: 28,
                    border: "none",
                    borderRadius: 999,
                    padding: 2,
                    cursor: "pointer",
                    background: formValues.marketing_agreed ? COLORS.buttonBg : "#d1d5db",
                    transition: "background 0.2s ease",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "#fff",
                      transform: formValues.marketing_agreed ? "translateX(18px)" : "translateX(0)",
                      transition: "transform 0.2s ease",
                    }}
                  />
                </button>
              </div>
            </div>

            <div style={fieldWrapStyle}>
              <span style={labelStyle}>문자 알림 수신 동의 (선택)</span>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  borderRadius: 10,
                  border: `1px solid ${COLORS.border}`,
                  background: "#fff",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, color: COLORS.text }}>상태</span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: formValues.sms_agreed ? "#166534" : COLORS.subText,
                      background: formValues.sms_agreed ? "#dcfce7" : "#f3f4f6",
                      borderRadius: 999,
                      padding: "4px 8px",
                    }}
                  >
                    {formValues.sms_agreed ? "동의" : "미동의"}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setFormValues((p) => ({ ...p, sms_agreed: !p.sms_agreed }))
                  }
                  aria-pressed={formValues.sms_agreed}
                  aria-label="문자 알림 수신 동의"
                  style={{
                    width: 46,
                    height: 28,
                    border: "none",
                    borderRadius: 999,
                    padding: 2,
                    cursor: "pointer",
                    background: formValues.sms_agreed ? COLORS.buttonBg : "#d1d5db",
                    transition: "background 0.2s ease",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "#fff",
                      transform: formValues.sms_agreed ? "translateX(18px)" : "translateX(0)",
                      transition: "transform 0.2s ease",
                    }}
                  />
                </button>
              </div>
            </div>

            {submitError && <p style={{ margin: 0, color: COLORS.error, fontSize: 13 }}>{submitError}</p>}
            {submitSuccess && <p style={{ margin: 0, color: "#16a34a", fontSize: 13 }}>변경사항이 저장되었습니다.</p>}

            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={!isDirty || isSubmitting}
              style={{
                padding: "14px 0", borderRadius: 12, border: "none",
                background: isDirty && !isSubmitting ? COLORS.buttonBg : COLORS.border,
                color: isDirty && !isSubmitting ? "#fff" : COLORS.subText,
                fontWeight: 700, fontSize: 15,
                cursor: isDirty && !isSubmitting ? "pointer" : "default",
                fontFamily: "inherit",
              }}
            >
              {isSubmitting ? "저장 중..." : "변경 저장"}
            </button>
          </section>

          {/* 시간대 설정 */}
          <TimeRangeSettings />

          {/* 탈퇴 섹션 */}
          <div style={{ textAlign: "center", paddingTop: 8 }}>
            <button
              type="button"
              onClick={() => setShowDeleteModal(true)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                color: "#dc2626", fontSize: 14, fontFamily: "inherit",
                textDecoration: "underline",
              }}
            >
              탈퇴하기
            </button>
          </div>
        </>
      )}

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        isDeleting={isDeleting}
        error={deleteError}
        onConfirm={() => void handleDelete()}
        onClose={() => { if (!isDeleting) setShowDeleteModal(false); }}
      />
      </div>
    </main>
  );
}
