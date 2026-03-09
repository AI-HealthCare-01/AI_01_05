import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMyInfo, updateMyInfo } from "../api/users";
import { Button } from "../components/Button";
import { ErrorMessage } from "../components/ErrorMessage";
import { Loading } from "../components/Loading";
import { COLORS } from "../constants/theme";
import type { UserMe } from "../types";

export function MyPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<UserMe | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");

  const fetchMe = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getMyInfo();
      setData(result);
      setNickname(result.nickname ?? "");
      setEmail(result.email ?? "");
    } catch {
      setError("내 정보를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchMe();
  }, []);

  const submit = async () => {
    try {
      setIsSubmitting(true);
      setError(null);
      await updateMyInfo({ nickname, email });
      await fetchMe();
    } catch {
      setError("내 정보 수정에 실패했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main style={{ background: COLORS.background, minHeight: "100vh", padding: 16, display: "grid", gap: 12 }}>
      <button
        onClick={() => navigate(-1)}
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "15px",
          color: COLORS.subText,
          fontWeight: 600,
          padding: "0 0 16px 0",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          fontFamily: "inherit",
        }}
      >
        ‹ 뒤로
      </button>
      <h1 style={{ margin: 0, color: COLORS.text, fontSize: 20 }}>마이페이지</h1>
      {isLoading ? <Loading /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => void fetchMe()} /> : null}
      {!isLoading && data ? (
        <section style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12, background: "#fff", display: "grid", gap: 8 }}>
          <input value={nickname} onChange={(event) => setNickname(event.target.value)} placeholder="닉네임" />
          <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="이메일" />
          <Button type="button" onClick={() => void submit()} loading={isSubmitting}>
            저장
          </Button>
        </section>
      ) : null}
    </main>
  );
}
