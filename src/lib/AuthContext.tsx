import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { AuthContext } from "./auth-context";
import { supabase } from "./supabase";

// BOHUMFIT-103: 카카오 로그아웃 시 카카오 브라우저 세션까지 만료(재로그인 자동로그인 방지)용 환경변수.
//   client_id = 카카오 REST API 키, logout_redirect_uri = 등록된 로그아웃 URI(기본 bohumfit.ai).
const KAKAO_REST_API_KEY = import.meta.env.VITE_KAKAO_REST_API_KEY;
const KAKAO_LOGOUT_REDIRECT_URI = import.meta.env.VITE_KAKAO_LOGOUT_REDIRECT_URI || "https://bohumfit.ai/";
const INACTIVITY_LIMIT_MS = 30 * 60 * 1000; // 30분 비활성 자동 로그아웃

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  // BOHUMFIT-103: 30분 비활성 자동 로그아웃(메모리 타이머 — localStorage 미사용).
  //   로그인 상태에서만 동작, 사용자 활동 시 타이머 리셋. 유휴 만료 시 앱 세션만 종료
  //   (전체 카카오 리다이렉트는 명시적 로그아웃 버튼에서만 — 유휴 시 갑작스런 이동 방지).
  useEffect(() => {
    if (!session) return;
    let timer = 0;
    const reset = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        void supabase.auth.signOut();
      }, INACTIVITY_LIMIT_MS);
    };
    const events: Array<keyof WindowEventMap> = ["mousedown", "keydown", "scroll", "touchstart"];
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset();
    return () => {
      window.clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [session]);

  const signOut = async () => {
    // signOut 전에 로그인 수단을 읽어둔다(이후 세션이 비워짐).
    const provider = session?.user?.app_metadata?.provider;
    await supabase.auth.signOut();
    // BOHUMFIT-103: 카카오 로그인 사용자만 카카오 세션 만료 페이지로 이동(앱키 설정 시).
    //   카카오 콘솔에 로그아웃 Redirect URI(VITE_KAKAO_LOGOUT_REDIRECT_URI) 등록 필요.
    //   이메일·구글 사용자는 리다이렉트 없이 일반 종료.
    if (provider === "kakao" && KAKAO_REST_API_KEY) {
      window.location.href =
        `https://kauth.kakao.com/oauth/logout?client_id=${encodeURIComponent(KAKAO_REST_API_KEY)}` +
        `&logout_redirect_uri=${encodeURIComponent(KAKAO_LOGOUT_REDIRECT_URI)}`;
    }
  };

  return (
    <AuthContext.Provider value={{ user: session?.user ?? null, session, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
