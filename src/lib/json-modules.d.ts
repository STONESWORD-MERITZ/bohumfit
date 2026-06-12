// BOHUMFIT-041: JSON 모듈 import 선언 (tsconfig 무수정 — resolveJsonModule 대체).
// Vite/Vitest 는 JSON import 를 네이티브 지원하며, 이 선언은 tsc 타입체크용이다.
// 값은 unknown 으로 두고 사용처(coverageMapping.ts)에서 타입 단언·검증한다.
declare module "*.json" {
  const value: unknown;
  export default value;
}
