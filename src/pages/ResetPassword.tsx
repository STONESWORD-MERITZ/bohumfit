import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Button from "../components/ui/Button";
import Callout from "../components/ui/Callout";
import { TextInput } from "../components/ui/Field";
import Logo from "../components/Logo";
import { supabase } from "../lib/supabase";

type ResetState = "checking" | "ready" | "invalid" | "done";

function hasRecoveryMarker() {
  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  return Boolean(search.get("code") || search.get("type") === "recovery" || hash.get("type") === "recovery");
}

export default function ResetPassword() {
  const [state, setState] = useState<ResetState>("checking");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function prepareRecoverySession() {
      if (!hasRecoveryMarker()) {
        setState("invalid");
        return;
      }

      const code = new URLSearchParams(window.location.search).get("code");
      if (code) {
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
        if (!active) return;
        if (exchangeError) {
          setState("invalid");
          return;
        }
        window.history.replaceState({}, document.title, "/reset-password");
      }

      const { data, error: sessionError } = await supabase.auth.getSession();
      if (!active) return;
      setState(!sessionError && data.session ? "ready" : "invalid");
    }

    void prepareRecoverySession();
    return () => {
      active = false;
    };
  }, []);

  async function submitNewPassword(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 10) {
      setError("새 비밀번호는 10자 이상으로 입력해 주세요.");
      return;
    }
    if (password !== passwordConfirm) {
      setError("새 비밀번호가 서로 일치하지 않습니다.");
      return;
    }

    setLoading(true);
    setError("");
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setError(updateError.message || "비밀번호 변경에 실패했습니다. 링크를 다시 요청해 주세요.");
      setLoading(false);
      return;
    }

    await supabase.auth.signOut();
    setState("done");
    setLoading(false);
  }

  return (
    <div className="flex min-h-dvh items-center justify-center overflow-x-clip bg-canvas px-4">
      <div className="w-full max-w-sm min-w-0">
        <div className="mb-8 text-center">
          <Logo size={34} variant="light" className="mx-auto max-w-full" />
          <p className="mt-3 text-body text-ink-soft">새 비밀번호를 설정합니다</p>
        </div>

        <section className="rounded-card border border-line bg-white p-6">
          {state === "checking" && (
            <p className="text-sm font-semibold text-ink-soft">재설정 링크를 확인하고 있습니다.</p>
          )}

          {state === "invalid" && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-extrabold text-ink-900">링크를 다시 요청해 주세요</p>
                <p className="mt-1 text-xs leading-5 text-ink-soft">
                  비밀번호 재설정 링크가 만료되었거나 올바르지 않습니다. 메일을 다시 받아 진행해 주세요.
                </p>
              </div>
              <Link to="/forgot-password" className="block rounded-btn bg-accent-600 px-4 py-3 text-center text-sm font-bold text-white">
                재설정 메일 다시 받기
              </Link>
            </div>
          )}

          {state === "ready" && (
            <form onSubmit={submitNewPassword} className="space-y-3">
              <div>
                <p className="text-sm font-extrabold text-ink-900">새 비밀번호 설정</p>
                <p className="mt-1 text-xs leading-5 text-ink-soft">이메일 가입 계정에 사용할 새 비밀번호를 입력해 주세요.</p>
              </div>
              <TextInput
                type="password"
                placeholder="새 비밀번호 10자 이상"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={10}
                required
                autoComplete="new-password"
              />
              <TextInput
                type="password"
                placeholder="새 비밀번호 확인"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                minLength={10}
                required
                autoComplete="new-password"
              />
              {error && <Callout variant="danger">{error}</Callout>}
              <Button type="submit" loading={loading} full size="lg">
                비밀번호 변경
              </Button>
            </form>
          )}

          {state === "done" && (
            <div className="space-y-4">
              <Callout>비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.</Callout>
              <Link to="/login" className="block rounded-btn bg-accent-600 px-4 py-3 text-center text-sm font-bold text-white">
                로그인으로 이동
              </Link>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
