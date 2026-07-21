// BOHUMFIT-236 E: 수동 담보 추가 — 설계사가 [최종] 비교표에 담보를 직접 추가/삭제한다.
// 세션 상태 전용(서버 저장 없음 — PII·저장 정책 유지). 병합 결과는 화면 표시와
// 엑셀/PDF 내보내기 payload에 함께 쓰인다(백엔드 ensure_comparison은 제공된
// comparison을 그대로 통과 — compare.py:411 실측).
import type { CoverageComparison, ComparisonRow } from "./coverageAfterDisplayCache";

export type ManualRider = {
  id: string;
  name: string;
  group12: string;
  amount: number;
  contractIdx?: string;
};

/** 표·내보내기에 쓰는 표시명 — "수동 입력" 구분을 이름에 고정(렌더러 무수정 반영). */
export function manualRiderRowName(rider: ManualRider): string {
  const origin = rider.contractIdx ? `수동·계약 ${rider.contractIdx}` : "수동";
  return `${rider.name} (${origin})`;
}

export function manualRiderRow(rider: ManualRider): ComparisonRow {
  return {
    group12: rider.group12 || "기타",
    kb_name: manualRiderRowName(rider),
    recommended: null,
    before_value: 0,
    after_value: rider.amount,
    before_gap: null,
    after_gap: null,
    before_status: null,
    after_status: null,
    status_change: "manual",
    delta_value: rider.amount,
    improved: false,
    worsened: false,
    manual: true,
  };
}

/** comparison에 수동 담보 행을 병합(원본 불변). 표·대분류 합계·내보내기가 함께 반영된다. */
export function mergeManualRiders(
  comparison: CoverageComparison,
  riders: ManualRider[],
): CoverageComparison {
  if (!riders.length) return comparison;
  return {
    ...comparison,
    coverages: [...comparison.coverages, ...riders.map(manualRiderRow)],
  };
}
