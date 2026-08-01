import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import { AuthContext } from "./auth-context";
import { supabase } from "./supabase";
// BOHUMFIT-265: 로그아웃·계정 전환 시 오프라인 캐시 삭제(A안).
import { clearAnalysisCache } from "./analysisCache";

// BOHUMFIT-103: 카카오 로그아웃 시 카카오 브라우저 세션까지 만료(재로그인 자동로그인 방지)용 환경변수.
//   client_id = 카카오 REST API 키, logout_redirect_uri = 등록된 로그아웃 URI(기본 bohumfit.ai).
const KAKAO_REST_API_KEY = import.meta.env.VITE_KAKAO_REST_API_KEY;
const KAKAO_LOGOUT_REDIRECT_URI = import.meta.env.VITE_KAKAO_LOGOUT_REDIRECT_URI || "https://bohumfit.ai/";
const INACTIVITY_LIMIT_MS = 30 * 60 * 1000; // 30분 비활성 자동 로그아웃

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * BOHUMFIT-265(보정): 직전 로그인 사용자 id.
   *   ★오프라인 캐시 삭제 판정의 유일한 기준 — "누가 로그인해 있었는가"가 바뀌는 순간만 지운다.
   */
  const lastUserIdRef = useRef<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      lastUserIdRef.current = data.session?.user?.id ?? null;
      setSession(data.session);
      setLoading(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      // BOHUMFIT-265(보정) — ★오프라인 분석 캐시 삭제의 **단일 지점**.
      //   호출부마다 삭제를 복제하지 않는다(249·251 선례). 로그아웃 경로가 여러 갈래이기 때문이다:
      //     ①명시적 로그아웃 버튼 ②30분 무활동 자동 종료(아래 타이머) ③비밀번호 변경 후 종료
      //     (`ResetPassword.tsx`) ④세션 만료·토큰 갱신 실패 ⑤다른 탭에서의 로그아웃.
      //   ①~⑤ 전부 결국 이 구독으로 흘러오므로, 여기 한 곳만 지키면 **새 경로가 생겨도 자동 포섭**된다.
      //   판정은 "이벤트 이름"이 아니라 **사용자 id 전이**로 한다(이벤트명은 SDK 버전에 따라 달라진다).
      const prevUserId = lastUserIdRef.current;
      const nextUserId = s?.user?.id ?? null;
      lastUserIdRef.current = nextUserId;
      // 로그인해 있던 사용자가 사라졌거나(로그아웃·만료) 다른 계정으로 바뀌면 기기 캐시를 전량 삭제한다.
      //   토큰 갱신(TOKEN_REFRESHED)처럼 같은 사용자가 유지되는 이벤트에서는 지우지 않는다.
      if (prevUserId && prevUserId !== nextUserId) void clearAnalysisCache().catch(() => {});
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
        // BOHUMFIT-265(보정): 여기서 캐시를 따로 지우지 않는다 — 세션이 사라지면 위 auth 구독이
        //   단일 지점에서 삭제한다(경로별 복제 금지).
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
    // BOHUMFIT-265(보정): 캐시 삭제는 위 auth 구독이 단일 지점으로 처리한다 — 여기서 중복 호출하지 않는다.
    await supabase.auth.signOut();
    // BOHUMFIT-103: 카카오 로그인 사용자만 카카오 세션 만료 페이지로 이동(앱키 설정 시).
    //   카카오 콘솔에 로그아웃 Redirect URI(VITE_KAKAO_LOGOUT_REDIRECT_URI) 등록 필요.
    //   이메일·구글 사용자는 리다이렉트 없이 일반 종료.
    if (provider === "kakao" && KAKAO_REST_API_KEY) {
      // ★이 경로만 예외: 즉시 외부 페이지로 이동하면 구독이 시작한 비동기 삭제가 중간에 끊길 수 있다.
      //   정책이 아니라 **이탈 직전 flush**이며, 삭제는 멱등이라 두 번 실행돼도 안전하다.
      await clearAnalysisCache().catch(() => {});
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
