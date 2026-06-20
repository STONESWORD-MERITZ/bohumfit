// BOHUMFIT-086: 휴대폰 인증 게이트 순수 판정 로직(React/Supabase 의존 없음 → 단위 테스트 용이).
//   085 버그(행 없음=통과)·086 진단을 반영: 행 없음·false=미인증, true·internal=통과,
//   조회 전/세션 로딩=loading, 진짜 조회 오류(스키마 부재 등)만 deploy-safe 통과.

export type PhoneGateStatus = "loading" | "anonymous" | "verified" | "unverified";

export type ProfileRow = { phone_verified?: boolean | null; role?: string | null } | null;

export type PhoneGateInput = {
  /** 인증 컨텍스트 세션 로딩 중 */
  authLoading: boolean;
  /** 로그인 사용자 존재 */
  hasUser: boolean;
  /** profiles 조회 결과(조회 완료 전이면 undefined) */
  query?: { data: ProfileRow; error: boolean };
};

/**
 * 게이트 판정.
 * - authLoading 또는 조회 미완료 → "loading"(판정 보류, 통과시키지 않음)
 * - 비로그인 → "anonymous"
 * - 조회 오류(테이블/컬럼 부재 등 스키마 문제·일시 오류) → "verified"(deploy-safe 통과, 잠금 방지)
 * - role === "internal" → "verified"(우회)
 * - 행 없음(data=null)·phone_verified !== true → "unverified"(★ 기존 "행 없으면 통과" 버그 차단)
 * - phone_verified === true → "verified"
 */
export function decidePhoneGate(input: PhoneGateInput): PhoneGateStatus {
  if (input.authLoading) return "loading";
  if (!input.hasUser) return "anonymous";
  if (!input.query) return "loading";
  if (input.query.error) return "verified";
  const data = input.query.data;
  if (data?.role === "internal") return "verified";
  return data?.phone_verified === true ? "verified" : "unverified";
}
