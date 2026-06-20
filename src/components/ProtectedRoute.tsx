import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { supabase } from "../lib/supabase";

// BOHUMFIT-075: 로그인 보호 + 휴대폰 본인인증 게이트(소셜·이메일 공통, DB 기준 일원화).
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  // 현재 사용자 기준 null=조회 중, true=통과(인증됨/게이트 비활성), false=미인증.
  const [phoneGate, setPhoneGate] = useState<{ userId: string; verified: boolean } | null>(null);
  const phoneVerified = user && phoneGate?.userId === user.id ? phoneGate.verified : null;

  useEffect(() => {
    if (!user) return;
    let alive = true;
    supabase
      .from("profiles")
      .select("phone_verified")
      .eq("id", user.id)
      .single()
      .then(({ data, error }) => {
        if (!alive) return;
        // 컬럼/행 없음·RLS·네트워크 오류 → 게이트 비활성(통과). 마이그레이션 미실행 시 안전.
        setPhoneGate({ userId: user.id, verified: error ? true : (data?.phone_verified ?? true) });
      });
    return () => {
      alive = false;
    };
  }, [user]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-400">로딩 중...</div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  // /phone-verify 자체는 게이트 제외(무한 리다이렉트 방지).
  if (location.pathname !== "/phone-verify") {
    if (phoneVerified === null) {
      return (
        <div className="flex min-h-screen items-center justify-center text-sm text-gray-400">로딩 중...</div>
      );
    }
    if (phoneVerified === false) return <Navigate to="/phone-verify" replace />;
  }

  return <>{children}</>;
}
