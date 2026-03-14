import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteMyAccount, getMyInfo, updateMyInfo } from "../api/users";
import { getMyCharacter } from "../apis/characterApi";
import { CHARACTER_IMAGE_BY_ID, DEFAULT_CHARACTER_IMAGE } from "../constants/characters";
import { COLORS } from "../constants/theme";
import { useAuthStore } from "../store/authStore";
import type { UserMe } from "../types";

// ─── 유효성 검사 ────────────────────────────────────────────────────────────

type FormFields = { nickname: string; email: string | null; birthday: string | null };
type FieldErrors = Partial<Record<keyof FormFields, string>>;

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

  const [formValues, setFormValues] = useState<FormFields & { gender: UserMe["gender"] }>({
    nickname: "", email: null, birthday: null, gender: "UNKNOWN",
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
    formValues.gender !== initialValues.gender;

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);
        const [me, char] = await Promise.allSettled([getMyInfo(), getMyCharacter()]);
        if (me.status === "fulfilled" && me.value) {
          const u = me.value;
          setUserInfo(u);
          const vals = { nickname: u.nickname, email: u.email, birthday: u.birthday, gender: u.gender };
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
        onClick={() => navigate(-1)}
        style={{
          background: "none", border: "none", cursor: "pointer", fontSize: 15,
          color: COLORS.subText, fontWeight: 600, padding: "16px 0",
          display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
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
