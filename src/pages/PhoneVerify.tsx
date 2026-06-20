// BOHUMFIT-075: 소셜/이메일 로그인 후 최초 1회 휴대폰 본인인증 게이트.
//   현재는 UI 게이트 — 실인증은 토스 본인인증 라이브 키 후 연동. 완료 시 /auth/verify-phone 영속.
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export default function PhoneVerify() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  // 085: ProtectedRoute가 전달한 원래 경로. 없으면 홈으로.
  const from = (location.state as { from?: string } | null)?.from;
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleVerify = async () => {
    const digits = phone.replace(/[^0-9]/g, "");
    if (digits.length < 10) {
      setError("휴대폰 번호를 정확히 입력해 주세요.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      // TODO(BOHUMFIT-074): 토스 본인인증 팝업 연동(라이브 키 후). 현재는 스텁 — 서버에 phone+phone_verified 영속(upsert).
      const token = session?.access_token;
      const r = await fetch(`${API_BASE}/auth/verify-phone`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ phone: digits }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        // 088: 동일 번호 중복가입 차단(409) → 명확한 한국어 안내.
        if (r.status === 409) {
          throw new Error(
            d.detail || "이미 인증에 사용된 번호입니다. 본인 명의의 다른 번호로 시도하거나 고객센터로 문의해 주세요.",
          );
        }
        throw new Error(d.detail || "본인인증에 실패했어요. 잠시 후 다시 시도해 주세요.");
      }
      // 085: 인증 성공 → profiles.phone_verified=true 영속됨. 원래 가려던 경로(없으면 홈)로 복귀.
      navigate(from || "/", { replace: true });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "본인인증에 실패했어요.");
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8F9FC] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-extrabold text-gray-900">휴대폰 본인인증</h1>
          <p className="mt-2 text-sm leading-6 text-gray-500 break-keep">
            1인 1계정 원칙에 따라 최초 1회 휴대폰 본인인증이 필요합니다.
          </p>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex gap-2">
            <input
              type="tel"
              inputMode="numeric"
              placeholder="휴대폰 번호 (- 없이)"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="min-w-0 flex-1 rounded-[8px] bg-white px-3 py-2.5 text-sm text-gray-800 shadow-[0_1px_3px_rgba(0,0,0,0.06)] placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
            />
          </div>
          {error && <p className="mt-2 text-xs font-semibold text-red-500">{error}</p>}
          <button
            type="button"
            onClick={handleVerify}
            disabled={busy}
            className="mt-4 w-full rounded-[8px] bg-accent-600 py-3 text-sm font-bold text-white shadow-[0_2px_8px_rgba(21,102,61,0.3)] transition-colors hover:bg-accent-700 disabled:opacity-50"
          >
            {busy ? "인증 중…" : "인증 요청"}
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            void signOut();
            navigate("/login", { replace: true });
          }}
          className="mt-6 w-full text-center text-xs text-gray-400 hover:underline"
        >
          다른 계정으로 로그인
        </button>
      </div>
    </div>
  );
}
