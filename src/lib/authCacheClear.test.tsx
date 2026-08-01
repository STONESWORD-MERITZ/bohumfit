// BOHUMFIT-265 보정 — ★모든 로그아웃 경로에서 오프라인 캐시가 실제로 전량 삭제되는지(실동작).
//   Codex 반려 1: 30분 무활동 자동 종료가 `supabase.auth.signOut()`을 직접 불러 삭제를 우회했다.
//   보정: 삭제를 auth 상태 구독 **한 곳**으로 모아, 어느 경로로 세션이 사라지든 포섭되게 했다.
//   실측한 로그아웃 경로(전수):
//     ①명시적 로그아웃 버튼(AuthContext.signOut) ②30분 무활동 자동 종료(AuthContext 타이머)
//     ③비밀번호 변경 후 종료(ResetPassword.tsx:75 — supabase를 직접 호출) ④세션 만료·토큰 갱신 실패
//     ⑤다른 탭에서의 로그아웃. ①~⑤ 모두 onAuthStateChange로 흘러온다.
import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Session } from "@supabase/supabase-js";

const clearAnalysisCache = vi.hoisted(() => vi.fn(async () => {}));
vi.mock("./analysisCache", () => ({ clearAnalysisCache }));

type Handler = (event: string, session: Session | null) => void;
const hooks = vi.hoisted(() => ({ handlers: [] as Handler[] }));

const supabaseMocks = vi.hoisted(() => ({
  getSession: vi.fn(async () => ({ data: { session: null as Session | null } })),
  signOut: vi.fn(async () => ({ error: null })),
  onAuthStateChange: vi.fn((fn: Handler) => {
    hooks.handlers.push(fn);
    return { data: { subscription: { unsubscribe: vi.fn() } } };
  }),
}));
vi.mock("./supabase", () => ({ supabase: { auth: supabaseMocks } }));

import { AuthProvider } from "./AuthContext";

/** 최소 세션 스텁 — 판정에 쓰는 것은 user.id뿐이다. */
const sessionOf = (id: string): Session =>
  ({ access_token: `t-${id}`, user: { id, app_metadata: {} } }) as unknown as Session;

/** 구독에 이벤트를 흘려보낸다(Supabase가 하는 일을 대신한다). */
function emit(event: string, session: Session | null) {
  act(() => {
    hooks.handlers.forEach((fn) => fn(event, session));
  });
}

const LOGGED_IN = sessionOf("user-1");

beforeEach(() => {
  hooks.handlers.length = 0;
  clearAnalysisCache.mockClear();
  supabaseMocks.signOut.mockClear();
  supabaseMocks.getSession.mockResolvedValue({ data: { session: LOGGED_IN } });
});

afterEach(() => {
  vi.useRealTimers();
});

/** 로그인 상태의 AuthProvider를 띄운다(구독 등록 + 초기 세션 반영까지). */
async function mountLoggedIn() {
  const utils = render(
    <AuthProvider>
      <div>앱</div>
    </AuthProvider>
  );
  await act(async () => {}); // getSession 프라미스 소진
  emit("INITIAL_SESSION", LOGGED_IN);
  clearAnalysisCache.mockClear(); // 로그인 진입은 삭제 대상이 아니다
  return utils;
}

describe("★로그아웃 3경로 — 캐시 전량 삭제", () => {
  it("① 수동 로그아웃(명시적 signOut) 시 삭제된다", async () => {
    await mountLoggedIn();
    // 사용자가 로그아웃 버튼을 누르면 Supabase가 세션을 비우고 이벤트를 흘린다.
    emit("SIGNED_OUT", null);
    expect(clearAnalysisCache).toHaveBeenCalledTimes(1);
  });

  it("② ★30분 무활동 자동 로그아웃에서도 삭제된다(Codex 반려 1의 결함 경로)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await mountLoggedIn();

    // 무활동 타이머 만료 → AuthContext가 supabase.auth.signOut()을 직접 호출한다.
    await act(async () => {
      vi.advanceTimersByTime(30 * 60 * 1000);
    });
    expect(supabaseMocks.signOut).toHaveBeenCalled();

    // 그 결과로 세션이 사라지면 구독이 삭제를 수행한다 — 타이머 경로에 삭제 코드가 없어도 포섭된다.
    emit("SIGNED_OUT", null);
    expect(clearAnalysisCache).toHaveBeenCalledTimes(1);
  });

  it("③ 세션 만료·토큰 갱신 실패(앱이 호출하지 않은 종료)에서도 삭제된다", async () => {
    await mountLoggedIn();
    // 갱신 실패는 앱 코드를 거치지 않고 세션만 사라진다.
    emit("TOKEN_REFRESHED", null);
    expect(clearAnalysisCache).toHaveBeenCalledTimes(1);
  });

  it("③' 비밀번호 변경 후 종료(ResetPassword가 supabase를 직접 호출)도 같은 경로로 포섭된다", async () => {
    await mountLoggedIn();
    emit("SIGNED_OUT", null);
    expect(clearAnalysisCache).toHaveBeenCalledTimes(1);
  });
});

describe("★삭제하지 말아야 할 때는 지우지 않는다", () => {
  it("토큰 갱신으로 같은 사용자가 유지되면 삭제하지 않는다", async () => {
    await mountLoggedIn();
    emit("TOKEN_REFRESHED", sessionOf("user-1"));
    expect(clearAnalysisCache).not.toHaveBeenCalled();
  });

  it("★계정 전환(다른 사용자 로그인)에서는 이전 사용자 캐시를 지운다", async () => {
    await mountLoggedIn();
    emit("SIGNED_IN", sessionOf("user-2"));
    expect(clearAnalysisCache).toHaveBeenCalledTimes(1);
  });

  it("비로그인 상태로 앱을 열 때는 저장소를 건드리지 않는다", async () => {
    supabaseMocks.getSession.mockResolvedValue({ data: { session: null } });
    render(
      <AuthProvider>
        <div>앱</div>
      </AuthProvider>
    );
    await act(async () => {});
    emit("INITIAL_SESSION", null);
    expect(clearAnalysisCache).not.toHaveBeenCalled();
  });
});
