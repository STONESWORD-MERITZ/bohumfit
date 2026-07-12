import { useState } from "react";
import { Link } from "react-router-dom";
import HCaptcha from "../components/HCaptcha";
import Logo from "../components/Logo";
import { isHCaptchaEnabled } from "../lib/hcaptcha";
import { supabase } from "../lib/supabase";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);
  const [agreePrivacy, setAgreePrivacy] = useState(false);
  const [agreeMedical, setAgreeMedical] = useState(false);
  const [phone, setPhone] = useState("");
  const [phoneVerified, setPhoneVerified] = useState(false);
  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaUnavailable, setCaptchaUnavailable] = useState(false);

  const requireCaptcha = () => {
    if (isHCaptchaEnabled() && !captchaUnavailable && !captchaToken) {
      setError("보안 확인을 완료해 주세요.");
      return false;
    }
    return true;
  };

  const requestPhoneVerify = () => {
    const digits = phone.replace(/[^0-9]/g, "");
    if (digits.length < 10) {
      setError("휴대폰 번호를 정확히 입력해 주세요.");
      return;
    }
    setError("");
    setPhoneVerified(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agreeTerms || !agreePrivacy || !agreeMedical || !phoneVerified) return;
    if (!requireCaptcha()) return;
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: captchaToken ? { captchaToken } : undefined,
    });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      setDone(true);
    }
  };

  const handleOAuth = async (provider: "kakao" | "google") => {
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.origin },
    });
    setLoading(false);
    if (error) setError(error.message);
  };

  if (done) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-[#F8F9FC] px-4">
        <div className="w-full max-w-sm text-center">
          <h2 className="mb-2 text-lg font-extrabold text-ink-900">이메일을 확인해 주세요</h2>
          <p className="mb-6 text-sm leading-6 text-ink-soft">
            {email} 주소로 인증 메일을 보냈습니다.
            <br />
            메일의 링크를 누르면 가입이 완료됩니다.
          </p>
          <Link to="/login" className="text-sm font-bold text-accent-600 hover:underline">
            로그인으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[#F8F9FC] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-10 text-center">
          <Logo size={34} variant="light" className="mx-auto" />
          <p className="mt-2 text-sm text-ink-soft">보험핏 계정 만들기</p>
        </div>

        <section className="rounded-[8px] border border-line bg-white p-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
          <p className="text-sm font-extrabold text-ink-900">소셜 계정으로 바로 시작하기</p>
          <p className="mt-1 text-xs leading-5 text-ink-soft">카카오 계정은 이메일 제공 여부와 관계없이 이용할 수 있습니다.</p>
          <div className="mt-3 space-y-2">
            <button
              type="button"
              onClick={() => void handleOAuth("kakao")}
              disabled={loading}
              className="flex w-full items-center justify-center rounded-[8px] py-3 text-sm font-bold transition-opacity hover:opacity-90 disabled:opacity-50"
              style={{ background: "#FEE500", color: "#191919" }}
            >
              카카오로 계속하기
            </button>
            <button
              type="button"
              onClick={() => void handleOAuth("google")}
              disabled={loading}
              className="flex w-full items-center justify-center rounded-[8px] border border-line-strong bg-white py-3 text-sm font-bold text-ink-800 transition-colors hover:bg-ink-50 disabled:opacity-50"
            >
              Google로 계속하기
            </button>
          </div>
          <HCaptcha
            onTokenChange={setCaptchaToken}
            onReady={() => setCaptchaUnavailable(false)}
            onUnavailable={() => setCaptchaUnavailable(true)}
            className="mt-4"
          />
        </section>

        <div className="my-6 flex items-center gap-3" aria-hidden>
          <div className="h-px flex-1 bg-line" />
          <span className="text-xs font-medium text-ink-400">이메일로 가입</span>
          <div className="h-px flex-1 bg-line" />
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="email"
            aria-label="이메일"
            placeholder="이메일"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-[8px] bg-white px-4 py-3 text-sm text-ink shadow-[0_1px_3px_rgba(0,0,0,0.06)] placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
          />
          <input
            type="password"
            aria-label="비밀번호 10자 이상"
            placeholder="비밀번호 10자 이상"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={10}
            className="w-full rounded-[8px] bg-white px-4 py-3 text-sm text-ink shadow-[0_1px_3px_rgba(0,0,0,0.06)] placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
          />

          <div className="rounded-[8px] border border-line bg-white p-3">
            <p className="text-[12px] font-semibold text-ink">휴대폰 본인인증 (필수)</p>
            <p className="mt-0.5 text-[11px] text-ink-soft">1인 1계정 원칙에 따라 휴대폰 본인인증이 필요합니다.</p>
            <div className="mt-2 flex gap-2">
              <input
                type="tel"
                inputMode="numeric"
                aria-label="휴대폰 번호"
                placeholder="휴대폰 번호 (- 없이)"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={phoneVerified}
                className="min-w-0 flex-1 rounded-[8px] bg-white px-3 py-2 text-sm text-ink shadow-[0_1px_3px_rgba(0,0,0,0.06)] placeholder:text-ink-400 focus:outline-none focus:ring-2 focus:ring-accent-600/30 disabled:bg-ink-50 disabled:text-ink-soft"
              />
              <button
                type="button"
                onClick={requestPhoneVerify}
                disabled={phoneVerified}
                className="shrink-0 rounded-[8px] border border-accent-600 px-3 py-2 text-[12px] font-bold text-accent-700 disabled:border-emerald-300 disabled:text-emerald-600"
              >
                {phoneVerified ? "인증 완료" : "인증 요청"}
              </button>
            </div>
            {phoneVerified && (
              <p className="mt-1.5 text-[11px] text-emerald-600">본인인증이 완료되었습니다.</p>
            )}
          </div>

          <div className="mt-4 space-y-2 text-sm">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                required
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
                className="mt-0.5 shrink-0"
              />
              <span>
                <a href="/terms-of-service" target="_blank" rel="noreferrer" className="font-semibold underline">이용약관</a>에 동의합니다 (필수)
              </span>
            </label>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                required
                checked={agreePrivacy}
                onChange={(e) => setAgreePrivacy(e.target.checked)}
                className="mt-0.5 shrink-0"
              />
              <span>
                <a href="/privacy-policy" target="_blank" rel="noreferrer" className="font-semibold underline">개인정보처리방침</a>에 동의합니다 (필수)
              </span>
            </label>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                required
                checked={agreeMedical}
                onChange={(e) => setAgreeMedical(e.target.checked)}
                className="mt-0.5 shrink-0"
              />
              <span>
                민감정보(건강·의료정보) 처리에 동의합니다. 동의하지 않을 경우 분석 기능 이용이 제한됩니다. (필수)
              </span>
            </label>
          </div>

          {error && <p className="text-xs font-semibold text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading || !agreeTerms || !agreePrivacy || !agreeMedical || !phoneVerified}
            className="w-full rounded-[8px] bg-accent-600 py-3 text-sm font-bold text-white shadow-[0_2px_8px_rgba(8,71,52,0.3)] transition-colors hover:bg-accent-700 disabled:opacity-50"
          >
            {loading ? "가입 중..." : !phoneVerified ? "휴대폰 본인인증 후 가입" : "회원가입"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-ink-soft">
          이미 계정이 있나요?{" "}
          <Link to="/login" className="font-bold text-accent-600 hover:underline">
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
}
