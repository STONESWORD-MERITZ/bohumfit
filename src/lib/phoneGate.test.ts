import { describe, expect, it } from "vitest";
import { decidePhoneGate } from "./phoneGate";

// BOHUMFIT-086: 게이트 판정 단위 테스트.
//   행 없음→미인증, false→미인증, true→통과, internal→우회, 로딩중→미판정.
describe("decidePhoneGate", () => {
  it("세션 로딩 중이면 loading(판정 보류)", () => {
    expect(decidePhoneGate({ authLoading: true, hasUser: false })).toBe("loading");
    expect(decidePhoneGate({ authLoading: true, hasUser: true })).toBe("loading");
  });

  it("비로그인은 anonymous", () => {
    expect(decidePhoneGate({ authLoading: false, hasUser: false })).toBe("anonymous");
  });

  it("로그인했지만 profiles 조회 완료 전이면 loading", () => {
    expect(decidePhoneGate({ authLoading: false, hasUser: true })).toBe("loading");
    expect(decidePhoneGate({ authLoading: false, hasUser: true, query: undefined })).toBe("loading");
  });

  it("★ profiles 행 없음(data=null)은 미인증 — 기존 '행 없으면 통과' 버그 차단", () => {
    expect(
      decidePhoneGate({ authLoading: false, hasUser: true, query: { data: null, error: false } }),
    ).toBe("unverified");
  });

  it("phone_verified=false 는 미인증", () => {
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { phone_verified: false }, error: false },
      }),
    ).toBe("unverified");
  });

  it("phone_verified=true 는 통과", () => {
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { phone_verified: true }, error: false },
      }),
    ).toBe("verified");
  });

  it("bohumfit_tier=internal 은 phone_verified 와 무관하게 우회(통과) — BOHUMFIT-240 P5", () => {
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { bohumfit_tier: "internal", phone_verified: false }, error: false },
      }),
    ).toBe("verified");
  });

  it("★role=advisor 여도 bohumfit_tier 가 internal 아니면 우회 안 함(fail-closed) — 231 계열 결함 차단", () => {
    // FitHere 전문가 등록으로 role=advisor가 되어도 tier=customer면 본인인증 요구.
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { role: "advisor", bohumfit_tier: "customer", phone_verified: false }, error: false },
      }),
    ).toBe("unverified");
  });

  it("bohumfit_tier 미지값·부재는 우회 안 함(fail-closed)", () => {
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { phone_verified: false }, error: false },
      }),
    ).toBe("unverified");
    // tier=internal 이 아닌 advisor 등 미지값도 우회 안 함
    expect(
      decidePhoneGate({
        authLoading: false,
        hasUser: true,
        query: { data: { bohumfit_tier: "advisor", phone_verified: true }, error: false },
      }),
    ).toBe("verified"); // phone_verified=true 라 통과(우회가 아니라 실인증 통과)
  });

  it("조회 오류(스키마 부재·일시 오류)는 deploy-safe 통과", () => {
    expect(
      decidePhoneGate({ authLoading: false, hasUser: true, query: { data: null, error: true } }),
    ).toBe("verified");
  });
});
