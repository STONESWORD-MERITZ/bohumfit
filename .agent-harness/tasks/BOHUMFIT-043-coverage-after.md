# BOHUMFIT-043 컨설팅 후(後) 상태 입력 + 후 비분표

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows), 화면 확인은 Human.

## 전제
- 042 머지(업로드→매핑→전 비분표) 완료. 051 머지(6ddb384) 상태 기준.
- 041 lib(coverageMapping.ts)에 후 모델 함수 존재: `applyConsultingPlan`(해지 제외+override bake),
  `buildAfterTable`(=applyConsultingPlan+buildCoverageTable), `buildCoverageTable`/`sumColumns`(전후 공용).
- 042 파서(coverageParse.ts): `parseSourceMatrix`·`applyManualAssignments`·`listAssignableTargets`·`MANUAL_EXCLUDE`.
- **산식 재구현 절대 금지** — 041 lib 호출만. 다른 페이지 무수정.

## 범위 (In)
- `src/components/coverage/CoverageTableView.tsx`(신규) — 전/후 공용 비분표 표(042 전 비분표 마크업 추출, 동일 레이아웃).
- `src/components/coverage/CoverageAfterSection.tsx`(신규) — 후 설계 UI + 후 비분표.
- `src/pages/CoverageAnalysis.tsx`(소형 편집) — 전 비분표를 CoverageTableView로 치환(파일 축소), 043 예고 자리를 CoverageAfterSection으로 교체.

### A. 기존 계약 처리 (해지/유지 + 감액)
- 계약 단위 유지/해지 토글. 해지 계약은 후 비분표에서 제외(applyConsultingPlan), 시각적 '해지' 표시.
- 유지 계약: 담보(행) 단위 감액 override(overrideAmountManwon) 입력 + 조정 보험료(overridePremiumWon) 입력.

### B. 신규 제안 계약 (042 업로드 재사용)
- 제안 상품 파일 업로드 → parseSourceMatrix(브라우저 내·비저장). 경고 목록 표시.
- 미매핑 보장명은 042 흐름대로 수동 배정(applyManualAssignments + listAssignableTargets).
- '직접 계약 추가'로 회사/상품/보험료 + 담보 행(보장명·가입금액) 수기 입력·보정(읽힘 실패 대비).
- id 충돌 방지: 업로드 계약 `prop-*`, 수기 계약 `manual-*` prefix.

### C. 후 비분표
- 후 = 유지(감액 반영) + 신규 제안. `applyConsultingPlan(...)` → `buildCoverageTable`(전과 동일 순수함수).
- 전과 동일 36행 레이아웃(CoverageTableView 공용). 사망분해·종수술 자동셋팅은 lib 결과 그대로.
- 종수술 suggested 셀 수정 가능, 수정 시 합계 재계산도 lib(sumColumns).
- 열 헤더에 유지/신규 배지. 하단에 "다음: 최종비교분석표(준비 중)" 자리(044 예고, 기능 없음).

### D. 데이터·동작 원칙
- 모든 입력 세션 내만(저장 안 함), 비저장 안내 유지. 전/후는 입력만 다르고 같은 순수함수로 계산.

## 디자인
- 후 비분표는 전과 동일 표(공용 컴포넌트). 컨트롤은 페이지 기존 Tailwind 관례 + ui Badge/Button 재사용.
- /coverage는 045 Mercury 미이행 페이지(045가 보장분석 제외) — 전/후 일관 위해 기존 페이지 톤 유지. 전면 ui 이행은 후속.

## 범위 밖 (Out)
- 044 최종비교분석표 기능. 041 lib 수정. 다른 페이지/실손/고지 수정.

## ENV
- 신규 섹션은 별도 컴포넌트로 분리(truncation 회피). 마운트 git 금지, 검증 /tmp, 실데이터 금지(익명 합성).

## 검증
- /tmp: 신규 컴포넌트+lib+ui strict tsc + 합성 데이터 후 비분표 계산 단위테스트(해지/감액/신규/전후 합계).
- Codex(Windows): `npx tsc -p tsconfig.app.json`/`tsconfig.node.json`, `npm run lint`, `npm test`, `npm run build` + /coverage 브라우저 스모크.

## 산출 기록
- handoff: 후 비분표 구성·감액 override 동작·신규 업로드 재사용·검증례. Next: Codex → Human → 044.
