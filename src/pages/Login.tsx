// BOHUMFIT-045: 로그인 Mercury 전환 — 인증 로직·링크 불변, 토큰 v2/ui 컴포넌트 적용.
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";
import Button from "../components/ui/Button";
import Callout from "../components/ui/Callout";
import { TextInput } from "../components/ui/Field";
import HCaptcha from "../components/HCaptcha";
import Logo from "../components/Logo";
import { isHCaptchaEnabled } from "../lib/hcaptcha";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaUnavailable, setCaptchaUnavailable] = useState(false);

  const requireCaptcha = () => {
    if (isHCaptchaEnabled() && !captchaUnavailable && !captchaToken) {
      setError("보안 확인을 완료해 주세요.");
      return false;
    }
    return true;
  };

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requireCaptcha()) return;
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
      options: captchaToken ? { captchaToken } : undefined,
    });
    setLoading(false);
    if (error) {
      // BOHUMFIT-097(버그3): 이메일 미확인 계정은 세션이 없어 가입화면 재유입 루프로 오인됨.
      //   'Email not confirmed' 를 감지해 재가입 대신 메일 링크 클릭을 안내한다(루프 차단).
      if (/email not confirmed|email_not_confirmed|not confirmed/i.test(error.message)) {
        setError("이메일 인증이 아직 완료되지 않았습니다. 받은 메일의 인증 링크를 먼저 눌러 주세요. (회원가입을 다시 하실 필요는 없습니다)");
      } else {
        setError(error.message);
      }
    } else {
      navigate("/");
    }
  };

  const handleKakao = async () => {
    setError("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
    if (error) setError(error.message);
  };

  const handleGoogle = async () => {
    setError("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) setError(error.message);
  };

  return (
    <div className="flex min-h-dvh items-center justify-center overflow-x-clip bg-canvas px-4">
      <div className="w-full max-w-sm min-w-0">
        <div className="mb-8 text-center">
          <h1 className="flex w-full min-w-0 justify-center overflow-visible">
            <Logo size={34} variant="light" className="mx-auto max-w-full" />
          </h1>
          <p className="mt-3 text-body text-ink-soft">보험 고지 리스크 점검을 시작하세요</p>
        </div>

        <div className="rounded-card border border-line bg-white p-6">
          <div>
            <p className="text-sm font-extrabold text-ink-900">소셜 계정으로 시작하기</p>
            <p className="mt-1 text-xs leading-5 text-ink-soft">카카오 또는 Google 계정으로 바로 로그인할 수 있습니다.</p>
          </div>
          <div className="mt-4 space-y-3">
            <button
              type="button"
              onClick={handleKakao}
              disabled={loading}
              className="flex w-full items-center justify-center rounded-btn py-3 text-sm font-semibold transition-opacity hover:opacity-90"
              style={{ background: "#FEE500", color: "#191919" }}
            >
              카카오로 시작하기
            </button>

            <button
              type="button"
              onClick={handleGoogle}
              disabled={loading}
              className="flex w-full items-center justify-center rounded-btn border border-line-strong bg-white py-3 text-sm font-semibold text-ink-800 transition-colors hover:bg-ink-50"
            >
              Google로 시작하기
            </button>
          </div>

          <HCaptcha
            onTokenChange={setCaptchaToken}
            onReady={() => setCaptchaUnavailable(false)}
            onUnavailable={() => setCaptchaUnavailable(true)}
            className="mt-4"
          />

          <div className="my-6 flex items-center gap-3" aria-hidden>
            <div className="h-px flex-1 bg-line" />
            <span className="text-caption font-medium text-ink-400">이메일로 계속</span>
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
            <div className="text-right">
              <Link to="/forgot-password" className="text-xs font-semibold text-accent-700 hover:underline">
                비밀번호 찾기
              </Link>
            </div>

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
