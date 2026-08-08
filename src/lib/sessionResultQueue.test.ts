/// <reference types="node" />
// BOHUMFIT-277(B-F3) — 세션 임시 결과의 소유자 바인딩·단일 삭제 계약.
//
//   ★275 B-F3 실측 결함: 전체 `AnalyzeResult`를 10분 보관하는데 저장 레코드에 소유자 id가 없고
//     복원 시 대조도 없어서 **A 분석 → 로그아웃 → 10분 내 B 로그인 → A 결과 복원**이 성립했다.
//     265의 단일 삭제 지점(IndexedDB)에도 이 키가 빠져 있었다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  SESSION_RESULT_KEY,
  SESSION_RESULT_TTL_MS,
  clearSessionResult,
  readSessionResult,
  saveSessionResult,
} from "./sessionResultQueue";

const ROOT = process.cwd();
const A = "user-a-id";
const B = "user-b-id";
const RESULT = { customer_name: "가상고객A", standard_reports: { Q3: [{ code: "I10" }] } };
const T0 = 1_700_000_000_000;

beforeEach(() => sessionStorage.clear());
afterEach(() => sessionStorage.clear());

describe("★계정 전환 누수 차단(B-F3)", () => {
  it("A가 저장한 결과를 B는 복원하지 못하고, 레코드도 폐기된다", () => {
    saveSessionResult(RESULT, A, T0);
    expect(readSessionResult(B, T0 + 1000)).toBeNull();
    // ★남의 결과를 그냥 두지 않는다 — 읽지 못했으면 지운다.
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });

  it("같은 사용자는 정상 복원된다(기능 회귀 0)", () => {
    saveSessionResult(RESULT, A, T0);
    const restored = readSessionResult<typeof RESULT>(A, T0 + 60_000);
    expect(restored?.result).toEqual(RESULT);
    expect(restored?.ts).toBe(T0);
  });

  it("★비로그인 진입 시 읽지 않고 삭제한다", () => {
    saveSessionResult(RESULT, A, T0);
    expect(readSessionResult(null, T0 + 1000)).toBeNull();
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });

  it("★비로그인 상태에서는 저장 자체를 하지 않는다", () => {
    saveSessionResult(RESULT, null, T0);
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });

  it("★277 이전 레코드(uid 없음)는 복원하지 않고 폐기한다", () => {
    sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify({ result: RESULT, ts: T0 }));
    expect(readSessionResult(A, T0 + 1000)).toBeNull();
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });

  it("TTL(10분)이 지나면 폐기한다(138 동작 유지)", () => {
    saveSessionResult(RESULT, A, T0);
    expect(readSessionResult(A, T0 + SESSION_RESULT_TTL_MS)).toBeNull();
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
    expect(SESSION_RESULT_TTL_MS).toBe(10 * 60 * 1000);
  });

  it("깨진 레코드도 조용히 폐기한다", () => {
    sessionStorage.setItem(SESSION_RESULT_KEY, "{not json");
    expect(readSessionResult(A, T0)).toBeNull();
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });

  it("clearSessionResult는 멱등이다", () => {
    saveSessionResult(RESULT, A, T0);
    clearSessionResult();
    clearSessionResult();
    expect(sessionStorage.getItem(SESSION_RESULT_KEY)).toBeNull();
  });
});

// ── 단일 삭제 계약 배선 ────────────────────────────────────────────────────
describe("★265 단일 삭제 지점에 이 키가 포함된다", () => {
  const auth = readFileSync(resolve(ROOT, "src/lib/AuthContext.tsx"), "utf8");

  it("사용자 id 전이 지점에서 세션 결과도 삭제한다", () => {
    // 265가 세운 구조(이벤트명이 아니라 id 전이)를 그대로 쓰고 **키만 추가**했다.
    expect(auth).toContain("prevUserId !== nextUserId");
    expect(auth).toContain("clearSessionResult()");
    const at = auth.indexOf("prevUserId !== nextUserId");
    const block = auth.slice(at, at + 400);
    expect(block).toContain("clearAnalysisCache()");
    expect(block).toContain("clearSessionResult()");
  });

  it("카카오 이탈 직전 flush에도 포함된다", () => {
    const at = auth.indexOf("kauth.kakao.com");
    expect(auth.slice(Math.max(0, at - 400), at)).toContain("clearSessionResult()");
  });

  it("★Disclosure는 sessionStorage를 직접 만지지 않는다(계약 우회 방지)", () => {
    const page = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    expect(page).not.toContain('sessionStorage.setItem("bohumfit_result"');
    expect(page).not.toContain('sessionStorage.getItem("bohumfit_result"');
    expect(page).toContain("saveSessionResult(");
    expect(page).toContain("readSessionResult<");
  });
});
