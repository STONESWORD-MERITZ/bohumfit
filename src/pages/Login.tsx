// BOHUMFIT-045: 로그인 Mercury 전환 — 인증 로직·링크 불변, 토큰 v2/ui 컴포넌트 적용.
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";
import Button from "../components/ui/Button";
import Callout from "../components/ui/Callout";
import { TextInput } from "../components/ui/Field";
import BrandWordmark from "../components/BrandWordmark";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      navigate("/");
    }
  };

  const handleKakao = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
  };

  const handleGoogle = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1>
            <BrandWordmark size="lg" />
          </h1>
          <p className="mt-3 text-body text-ink-soft">보험 고지 리스크 점검을 시작하세요</p>
        </div>

        <div className="rounded-card border border-line bg-white p-6">
          <div className="space-y-3">
            <button
              onClick={handleKakao}
              className="flex w-full items-center justify-center rounded-btn py-3 text-sm font-semibold transition-opacity hover:opacity-90"
              style={{ background: "#FEE500", color: "#191919" }}
            >
              카카오로 시작하기
            </button>

            <button
              onClick={handleGoogle}
              className="flex w-full items-center justify-center rounded-btn border border-line-strong bg-white py-3 text-sm font-semibold text-ink-800 transition-colors hover:bg-ink-50"
            >
              Google로 시작하기
            </button>
          </div>

          <div className="my-6 flex items-center gap-3" aria-hidden>
            <div className="h-px flex-1 bg-line" />
            <span className="text-caption font-medium text-ink-400">또는</span>
            <div className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={handleEmail} className="space-y-3">
            <TextInput
              type="email"
              placeholder="이메일"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <TextInput
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />

            {error && <Callout variant="danger">{error}</Callout>}

            <Button type="submit" loading={loading} full size="lg">
              {loading ? "로그인 중..." : "이메일로 로그인"}
            </Button>
          </form>
        </div>

        <p className="mt-6 text-center text-caption text-ink-soft">
          아직 계정이 없나요?{" "}
          <Link to="/signup" className="font-semibold text-accent-700 hover:underline">
            회원가입
          </Link>
        </p>
        <p className="mt-3 text-center text-caption text-ink-soft">
          고객용 점검도{" "}
          <Link to="/check" className="font-semibold text-accent-700 hover:underline">
            로그인 후 이용
          </Link>
          할 수 있습니다.
        </p>
      </div>
    </div>
  );
}
