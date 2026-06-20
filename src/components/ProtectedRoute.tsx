import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { supabase } from "../lib/supabase";

// BOHUMFIT-075/085: 로그인 보호 + 휴대폰 본인인증 게이트(소셜·이메일 공통, DB 기준 일원화).
//   085: profiles 행 없음=미인증으로 판정(기존 "행 없으면 통과" 버그 수정). internal 역할은 우회.
//   단, 스키마 미존재(마이그레이션 미실행)·일시 오류는 잠금 방지를 위해 통과(deploy-safe).
export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  // 현재 사용자 기준 null=조회 중, true=통과(인증됨/internal/게이트 비활성), false=미인증.
  const [phoneGate, setPhoneGate] = useState<{ userId: string; verified: boolean } | null>(null);
  const phoneVerified = user && phoneGate?.userId === user.id ? phoneGate.verified : null;

  useEffect(() => {
    if (!user) return;
    let alive = true;
    supabase
      .from("profiles")
      .select("phone_verified, role")
      .eq("id", user.id)
      .maybeSingle()
      .then(({ data, error }) => {
        if (!alive) return;
        if (error) {
          // 테이블/컬럼 미존재(마이그레이션 미실행)·RLS·네트워크 오류 → 게이트 비활성(통과). 잠금 방지.
          setPhoneGate({ userId: user.id, verified: true });
          return;
        }
        // internal 역할은 게이트 우회. 행 없음(data=null)·false → 미인증(★ 행 없음 통과 버그 수정).
        const verified = data?.role === "internal" ? true : data?.phone_verified === true;
        setPhoneGate({ userId: user.id, verified });
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
    if (phoneVerified === false) {
      // 085: 인증 후 원래 가려던 경로로 복귀할 수 있도록 from 전달.
      return <Navigate to="/phone-verify" replace state={{ from: location.pathname + location.search }} />;
    }
  }

  return <>{children}</>;
}
