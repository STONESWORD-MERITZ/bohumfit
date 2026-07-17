import { useState } from "react";
import { Link } from "react-router-dom";
import Button from "../components/ui/Button";
import Callout from "../components/ui/Callout";
import { TextInput } from "../components/ui/Field";
import HCaptcha from "../components/HCaptcha";
import Logo from "../components/Logo";
import { supabase } from "../lib/supabase";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const RESET_SENT_MESSAGE = "입력한 이메일로 비밀번호 재설정 안내를 보냈습니다. 메일함에서 링크를 확인해 주세요.";

type SmsStep = "phone" | "code" | "password" | "done";
type ResetMode = "email" | "sms";

function isSmsPasswordResetEnabled() {
  return import.meta.env.VITE_ENABLE_SMS_PASSWORD_RESET === "true";
}

export default function ForgotPassword() {
  const smsEnabled = isSmsPasswordResetEnabled();
  const [mode, setMode] = useState<ResetMode>("email");
  const [smsStep, setSmsStep] = useState<SmsStep>("phone");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaUnavailable, setCaptchaUnavailable] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const digits = phone.replace(/[^0-9]/g, "");

  async function post(path: string, body: Record<string, unknown>) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(captchaToken && !captchaUnavailable ? { "x-hcaptcha-token": captchaToken } : {}),
      },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "요청을 처리하지 못했습니다.");
    return data;
  }

  async function requestEmailReset(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("이메일을 입력해 주세요.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    const redirectTo = `${window.location.origin}/reset-password`;

    try {
      await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo });
    } catch {
      // 계정 존재 여부와 운영 오류가 화면에서 계정 열거 신호가 되지 않도록 동일한 안내를 유지한다.
    } finally {
      setMessage(RESET_SENT_MESSAGE);
      setLoading(false);
    }
  }

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    if (digits.length < 10) {
      setError("등록 휴대폰 번호를 정확히 입력해 주세요.");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const data = await post("/auth/password-reset/request", { phone: digits });
      setMessage(data.message || "인증번호를 보냈습니다.");
      setSmsStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증번호 발송에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await post("/auth/password-reset/verify", { phone: digits, code });
      setResetToken(data.reset_token || "");
      setMessage(data.message || "휴대폰 인증이 완료되었습니다.");
      setSmsStep("password");
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증번호 확인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmPassword(e: React.FormEvent) {
    e.preventDefault();
    if (newPassword.length < 10) {
      setError("새 비밀번호는 10자 이상으로 입력해 주세요.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await post("/auth/password-reset/confirm", { reset_token: resetToken, password: newPassword });
      setMessage(data.message || "비밀번호가 변경되었습니다.");
      setSmsStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "비밀번호 변경에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  const showSms = smsEnabled && mode === "sms";

  return (
    <div className="flex min-h-dvh items-center justify-center overflow-x-clip bg-canvas px-4">
      <div className="w-full max-w-sm min-w-0">
        <div className="mb-8 text-center">
          <Logo size={34} variant="light" className="mx-auto max-w-full" />
          <p className="mt-3 text-body text-ink-soft">이메일 링크로 비밀번호를 재설정합니다</p>
        </div>

        <section className="rounded-card border border-line bg-white p-6">
          <div>
            <p className="text-sm font-extrabold text-ink-900">비밀번호 찾기</p>
            <p className="mt-1 text-xs leading-5 text-ink-soft">
              이메일 가입 계정만 비밀번호를 재설정할 수 있습니다. 카카오·Google 계정은 해당 소셜 버튼으로 로그인해 주세요.
            </p>
          </div>

          {smsEnabled && (
            <div className="mt-5 grid grid-cols-2 rounded-btn bg-ink-50 p-1 text-xs font-bold text-ink-soft" role="tablist" aria-label="비밀번호 재설정 방식">
              <button
                type="button"
                onClick={() => {
                  setMode("email");
                  setError("");
                  setMessage("");
                }}
                className={`rounded-[8px] px-3 py-2 ${mode === "email" ? "bg-white text-ink shadow-sm" : ""}`}
              >
                이메일
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("sms");
                  setError("");
                  setMessage("");
                }}
                className={`rounded-[8px] px-3 py-2 ${mode === "sms" ? "bg-white text-ink shadow-sm" : ""}`}
              >
                SMS
              </button>
            </div>
          )}

          {!showSms && (
            <form onSubmit={requestEmailReset} className="mt-5 space-y-3">
              <TextInput
                type="email"
                placeholder="가입 이메일"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
              {error && <Callout variant="danger">{error}</Callout>}
              {message && <Callout>{message}</Callout>}
              <Button type="submit" loading={loading} full size="lg">
                재설정 메일 받기
              </Button>
            </form>
          )}

          {showSms && smsStep === "phone" && (
            <form onSubmit={requestCode} className="mt-5 space-y-3">
              <TextInput
                type="tel"
                inputMode="numeric"
                placeholder="등록 휴대폰 번호 (- 없이)"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                autoComplete="tel"
              />
              <HCaptcha
                onTokenChange={setCaptchaToken}
                onReady={() => setCaptchaUnavailable(false)}
                onUnavailable={() => setCaptchaUnavailable(true)}
              />
              {error && <Callout variant="danger">{error}</Callout>}
              {message && <Callout>{message}</Callout>}
              <Button type="submit" loading={loading} full size="lg">
                인증번호 받기
              </Button>
            </form>
          )}

          {showSms && smsStep === "code" && (
            <form onSubmit={verifyCode} className="mt-5 space-y-3">
              <TextInput
                type="text"
                inputMode="numeric"
                placeholder="인증번호 6자리"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
                required
              />
              {error && <Callout variant="danger">{error}</Callout>}
              {message && <Callout>{message}</Callout>}
              <Button type="submit" loading={loading} full size="lg">
                인증번호 확인
              </Button>
              <button type="button" onClick={() => setSmsStep("phone")} className="w-full text-xs font-semibold text-ink-soft hover:underline">
                번호 다시 입력
              </button>
            </form>
          )}

          {showSms && smsStep === "password" && (
            <form onSubmit={confirmPassword} className="mt-5 space-y-3">
              <TextInput
                type="password"
                placeholder="새 비밀번호 10자 이상"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={10}
                required
                autoComplete="new-password"
              />
              {error && <Callout variant="danger">{error}</Callout>}
              {message && <Callout>{message}</Callout>}
              <Button type="submit" loading={loading} full size="lg">
                새 비밀번호 설정
              </Button>
            </form>
          )}

          {showSms && smsStep === "done" && (
            <div className="mt-5 space-y-4">
              <Callout>{message || "비밀번호가 변경되었습니다."}</Callout>
              <Link to="/login" className="block rounded-btn bg-accent-600 px-4 py-3 text-center text-sm font-bold text-white">
                로그인으로 돌아가기
              </Link>
            </div>
          )}
        </section>

        <p className="mt-6 text-center text-caption text-ink-soft">
          기억나셨나요?{" "}
          <Link to="/login" className="font-semibold text-accent-700 hover:underline">
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
}
