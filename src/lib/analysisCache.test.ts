// BOHUMFIT-265 — P3 오프라인 캐시(A안) 테스트: 24h 만료 · 5건 상한 · 로그아웃 삭제 · 비로그인 차단 ·
//   고지 문구 정합 · 264 PII 캐시 가드와의 분리(별도 스토어).
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MAX_ENTRIES, TTL_MS, isEntryValid, pickRetained, listAnalyses, getAnalysis, type CachedAnalysis } from "./analysisCache";

const ROOT = process.cwd();
const entry = (over: Partial<CachedAnalysis> = {}): CachedAnalysis => ({
  id: "a1",
  userId: "u1",
  savedAt: 1_000_000,
  label: "고객 A · 2026-07-31",
  payload: { ok: true },
  ...over,
});

describe("정책 상수", () => {
  it("최근 5건 · 24시간 만료(A안)", () => {
    expect(MAX_ENTRIES).toBe(5);
    expect(TTL_MS).toBe(24 * 60 * 60 * 1000);
  });
});

describe("만료·소유자 판정", () => {
  it("24시간 이내면 유효하다", () => {
    const e = entry();
    expect(isEntryValid(e, "u1", e.savedAt + TTL_MS - 1)).toBe(true);
  });

  it("★정확히 24시간이 지나면 만료된다", () => {
    const e = entry();
    expect(isEntryValid(e, "u1", e.savedAt + TTL_MS)).toBe(false);
    expect(isEntryValid(e, "u1", e.savedAt + TTL_MS + 60_000)).toBe(false);
  });

  it("★다른 사용자의 항목은 유효하지 않다(계정 전환 노출 0)", () => {
    const e = entry();
    expect(isEntryValid(e, "u2", e.savedAt + 1000)).toBe(false);
  });
});

describe("보관 상한", () => {
  it("최신 5건만 남기고 오래된 것부터 버린다", () => {
    const rows = Array.from({ length: 8 }, (_, i) => entry({ id: `a${i}`, savedAt: 1000 + i }));
    const kept = pickRetained(rows);
    expect(kept).toHaveLength(MAX_ENTRIES);
    expect(kept.map((r) => r.id)).toEqual(["a7", "a6", "a5", "a4", "a3"]);
  });
});

describe("★비로그인 차단", () => {
  it("userId가 없으면 목록·단건 모두 빈 결과(저장소를 열지 않는다)", async () => {
    await expect(listAnalyses(null)).resolves.toEqual([]);
    await expect(listAnalyses(undefined)).resolves.toEqual([]);
    await expect(listAnalyses("")).resolves.toEqual([]);
    await expect(getAnalysis("a1", null)).resolves.toBeNull();
  });
});

describe("★로그아웃 삭제 배선 — 단일 지점(복제 금지)", () => {
  // 실동작(수동·무활동·세션 만료·계정 전환)은 `authCacheClear.test.tsx`가 검증한다.
  //   여기서는 삭제가 **경로별로 복제되지 않았는지**라는 구조 계약만 고정한다.
  const src = readFileSync(join(ROOT, "src/lib/AuthContext.tsx"), "utf8");

  it("삭제 판정이 auth 상태 구독 안에 있다", () => {
    const from = src.indexOf("onAuthStateChange");
    const subscription = src.slice(from, src.indexOf("return () => listener", from));
    expect(subscription).toContain("clearAnalysisCache()");
    // ★이벤트 이름이 아니라 사용자 id 전이로 판정한다(SDK 버전에 따라 이벤트명이 달라지므로).
    expect(subscription).toContain("prevUserId");
    expect(subscription).toContain("nextUserId");
  });

  it("★무활동 자동 로그아웃 타이머에는 삭제를 복제하지 않는다(구독이 포섭)", () => {
    const from = src.indexOf("INACTIVITY_LIMIT_MS)");
    const timerBody = src.slice(src.indexOf("const reset"), from);
    expect(timerBody).not.toContain("clearAnalysisCache()");
  });

  it("카카오 리다이렉트 직전에만 flush를 둔다(이탈로 비동기 삭제가 끊기는 것 방지)", () => {
    const from = src.indexOf("const signOut");
    const signOutBody = src.slice(from, src.indexOf("\n  };", from));
    // 서버 로그아웃 자체에는 삭제를 붙이지 않는다 — 구독이 처리한다.
    expect(signOutBody.indexOf("clearAnalysisCache()")).toBeGreaterThan(
      signOutBody.indexOf("supabase.auth.signOut()")
    );
    // flush는 외부 페이지로 이동하기 직전에 있어야 의미가 있다.
    expect(signOutBody.indexOf("clearAnalysisCache()")).toBeLessThan(signOutBody.indexOf("window.location.href"));
  });
});

describe("★264 PII 캐시 가드와의 분리", () => {
  it("서비스워커는 분석·API 응답을 여전히 캐시하지 않는다(별도 스토어 사용)", () => {
    // sw.js의 차단 목록은 정규식 리터럴(`/\/api\//i`)이라 슬래시가 이스케이프돼 있다 —
    //   경로 형태로 비교하기 위해 `\/`를 `/`로 되돌린 뒤 검사한다(실측으로 정정).
    const sw = readFileSync(join(ROOT, "public/sw.js"), "utf8").replace(/\\\//g, "/");
    for (const blocked of ["/api/", "/coverage/", "/analyze", "/auth/", "/rest/v1/"]) {
      expect(sw).toContain(blocked);
    }
    // ★265가 264의 단일 판정 함수를 넓히지 않았음을 고정한다(PII는 여전히 SW 캐시 대상 밖).
    expect(sw).toContain("function isCacheableRequest");
    // 오프라인 캐시는 SW가 아니라 앱이 IndexedDB에 직접 넣는다.
    const cache = readFileSync(join(ROOT, "src/lib/analysisCache.ts"), "utf8");
    expect(cache).toContain("indexedDB");
    expect(cache).not.toContain("caches.open");
  });
});

describe("★고지 문구 3층 정합 (동의 화면 ↔ 개인정보처리방침)", () => {
  const consent = readFileSync(join(ROOT, "src/components/ConsentGate.tsx"), "utf8");
  const policy = readFileSync(join(ROOT, "src/pages/PrivacyPolicy.tsx"), "utf8");

  it("동의 화면이 90일·7일·24시간 세 층을 모두 고지한다", () => {
    expect(consent).toContain("자료 원본은 분석 후 저장하지 않습니다");
    expect(consent).toContain("90일간"); // 히스토리 저장 요청분(서버)
    expect(consent).toContain("7일간"); // 요약 자동 기록(서버)
    expect(consent).toContain("24시간 임시 보관"); // 기기 캐시(A안)
    expect(consent).toContain("로그아웃 시 즉시 삭제");
  });

  it("★동의 화면이 방침과 모순되는 단언을 하지 않는다(Codex 반려 2)", () => {
    // 방침은 분석 결과를 90일·7일 서버 보관한다고 명시한다 — "분석 결과는 서버에 저장하지 않는다"류의
    //   단언이 동의 화면에 남아 있으면 두 문서가 정면으로 충돌한다.
    //   ★검사 대상은 **화면에 렌더되는 문구**다 — 변경 사유를 적은 주석까지 잡으면 오탐이라 먼저 걷어낸다.
    const rendered = consent
      .replace(/\{\/\*[\s\S]*?\*\/\}/g, "")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    expect(rendered).not.toContain("분석 결과는 서버에 저장하지 않");
    expect(rendered).not.toContain("업로드 자료와 분석 결과는");
    expect(rendered).not.toContain("서버에 저장하지 않으며");
  });

  it("방침 쪽 근거 조항이 실제로 존재한다(동의 화면 수치의 출처)", () => {
    expect(policy).toContain("저장일부터 90일간 보관하며"); // 40·50행 계열
    expect(policy).toContain("최근 10건 범위에서 자동 기록되며, 7일이 지나면 자동 파기"); // 41·51행 계열
    expect(policy).toContain("최근 분석 5건이 이용자 기기(브라우저 저장소)에 24시간 동안 임시 보관");
    expect(policy).toContain("로그아웃 시 즉시 삭제됩니다");
  });

  it("기기 캐시 수치가 구현 상수와 일치한다(문구만 바뀌는 것을 막는다)", () => {
    expect(MAX_ENTRIES).toBe(5);
    expect(TTL_MS / (60 * 60 * 1000)).toBe(24);
    expect(consent).toContain("최근 5건");
    expect(policy).toContain("최근 분석 5건");
  });
});
