/* eslint-disable react-refresh/only-export-components */
// BOHUMFIT-086: 휴대폰 인증 게이트 공용 훅·래퍼.
//   ProtectedRoute(로그인 필수 라우트)와 PhoneGate(로그인 후 도착하는 공개 랜딩)에서 함께 사용해
//   "소셜 로그인 직후 공개 라우트(/)로 떨어져 게이트를 안 거치던" 미동작을 차단한다.
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./auth-context";
import { supabase } from "./supabase";
import { decidePhoneGate, type PhoneGateStatus, type ProfileRow } from "./phoneGate";

/** 현재 로그인 사용자의 휴대폰 인증 게이트 상태를 조회·판정한다. */
export function usePhoneGateStatus(): PhoneGateStatus {
  const { user, loading } = useAuth();
  const [result, setResult] = useState<{ userId: string; data: ProfileRow; error: boolean } | null>(null);

  useEffect(() => {
    if (!user) {
      return;
    }
    let alive = true;
    supabase
      .from("profiles")
      .select("phone_verified, role")
      .eq("id", user.id)
      .maybeSingle()
      .then(({ data, error }) => {
        if (!alive) return;
        setResult({ userId: user.id, data: (data as ProfileRow) ?? null, error: !!error });
      });
    return () => {
      alive = false;
    };
  }, [user]);

  // 사용자 전환 시 stale 결과 무시(조회 보류=loading).
  const query = user && result?.userId === user.id ? { data: result.data, error: result.error } : undefined;
  return decidePhoneGate({ authLoading: loading, hasUser: !!user, query });
}

/**
 * 공개 라우트에서도 "로그인했지만 미인증" 사용자를 휴대폰 인증으로 보낸다.
 * 비로그인·인증완료·로딩 중에는 children을 그대로 렌더(공개 페이지 정상 노출).
 * 소셜/이메일 로그인 후 도착하는 랜딩(/)에 적용해 게이트 누락을 막는다.
 */
export function PhoneGate({ children }: { children: ReactNode }) {
  const status = usePhoneGateStatus();
  const location = useLocation();
  if (status === "unverified" && location.pathname !== "/phone-verify") {
    return <Navigate to="/phone-verify" replace state={{ from: location.pathname + location.search }} />;
  }
  return <>{children}</>;
}
