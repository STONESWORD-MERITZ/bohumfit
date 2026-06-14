# BOHUMFIT-044 최종비교분석표 — 전/후 요약 비교

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows), 화면 확인은 Human.

## 전제
- 043 머지(158a87b): 전 비분표 + 후 비분표(해지/유지·감액·신규) 완료.
- 041 lib 전/후 집계값(sumColumns 결과)을 그대로 사용 — **산식 재구현 금지**. 다른 페이지 무수정.

## 범위 (In)
- `src/components/coverage/FinalComparison.tsx`(신규) — 최종비교분석표.
- `src/components/coverage/CoverageAfterSection.tsx`(소형 편집) — `beforeTotals` prop 추가 + 후 비분표 아래 FinalComparison 렌더.
- `src/pages/CoverageAnalysis.tsx`(소형 편집) — CoverageAfterSection 에 `beforeTotals={totals}`(전 표 합계) 전달.

### A. 주요보장 전/후 비교 (3열 메인표)
- [리모델링 전 금액] | [항목명] | [리모델링 후 금액], 약 37행(양식 순서).
- 값 = 041 집계값(beforeTotals/afterTotals)에서 항목→카테고리 id 매핑 합산. 재계산 없음.
- 증감 색상: 증가=강조(accent/페리윙클), 감소·해지=경고(warning/danger), 동일=뉴트럴.

### B. 암입원 처리 (표시 전용)
- lib 표준 카테고리는 암입원이 질병입원(disease_hospitalization)에 병합됨.
- 최종표는 암입원을 **별도 행으로 표시하되 값 분리 불가** → ids 없는 표시 전용 행 + "질병입원에 포함" 주석. 질병입원 행에 "암입원 포함" 주석.
- 일반입원도 lib 미분류(원천이 질병/상해입원 매핑) → 표시 전용 행 처리.
- lib 카테고리 확장(암입원 신설)은 범위 밖 — handoff 백로그.

### C. 핵심 질병 전→후 요약 (우측)
- 암 / 뇌초기 / 뇌중기 / 뇌말기 / 심장초기 / 심장말기 → 각 [전] → [후] 화살표(증감 방향·색).
- 매핑: 암=cancer_diagnosis, 뇌초기=cerebrovascular_early, 뇌중기=stroke_mid, 뇌말기=cerebral_hemorrhage_late, 심장초기=ischemic_heart_early, 심장말기=ami_late.
- 하단 '특이사항' 자유 입력(textarea, 세션 내 비저장).

### D. 동작·디자인
- 전/후 데이터는 043 계산 결과 재사용(재계산 금지). 045 Mercury 토큰·ui(Card/Badge) 재사용, 표는 CoverageTableView 패턴.
- 하단 "다음: 엑셀 출력(준비 중)" 자리(045 예고, 기능 없음). 비저장 안내 유지.

## 죽음 분해 표시 주의
- 양식에 재해사망 행이 없음 → 상해사망 행 = injury_death + disaster_death 합산 표시(분해 잔액 손실 방지, 표시 전용 결합). handoff 명시.

## 범위 밖 (Out)
- 045 엑셀 출력 기능. 041 lib 카테고리 확장(암입원). 다른 페이지/실손/고지 수정.

## ENV
- 신규 컴포넌트 분리(FinalComparison.tsx) truncation 회피. 마운트 git 금지, 검증 /tmp, 실데이터 금지(익명 합성).

## 검증
- /tmp: strict tsc(신규+lib+ui) + 합성 전/후 요약 단위테스트(증감·합계·화살표 방향).
- Codex(Windows): tsc(app/node)·lint·test·build + /coverage 스모크.

## 산출 기록
- handoff: 최종표 구성·암입원 처리·상해사망 결합·화살표 요약·특이사항·검증례. Next: Codex → Human → 045.
