# BOHUMFIT-048 설계사 우선 모드 + 고객 동의 게이트 + 모바일 동선

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 산식 무수정, 업로드·동의·모바일 UX만.

## 전제
- 046 보라 토큰·ui 재사용. 라우팅 대규모 변경 금지. 저장 X·면책·동의 기조 보존.
- Disclosure.tsx는 이미 설계사(agent) 모드 + 정보주체(고객) 동의 게이트(consent·subjectConsent, 버튼 게이팅) 보유 → **중복 게이트 금지, 무수정**.

## A. 고객 동의 게이트 (보장분석·실손 — 누락분 보강)
- 신규 `src/components/ConsentGate.tsx`(재사용): "설계사가 고객 본인 자료를 대신 업로드 → 고객에게 안내·동의 확보" 체크 + 비저장·고객 보유 안내 + 개인정보처리방침 링크. 미동의 시 업로드/분석 불가.
- `CoverageAnalysis.tsx`(보장분석 xlsx 업로드): 동의 전 파일 입력 비활성.
- `InsuranceCalculator.tsx`(실손 PDF 모드): 동의 전 '진료비 추출' 비활성.

## B. 모바일 우선
- 탭 타깃 44px+: `ui/Button.tsx` md/lg `min-h-[2.75rem]`. ConsentGate 체크 라벨 행 min-h-11·체크박스 h-5 w-5.
- 데스크탑 회귀 없게(44px는 데스크탑도 무해). 기존 표는 overflow-x-auto 유지(가로스크롤 대응).

## C. 결과 보유 원칙
- 결과 저장 안 함·출력물 고객 보유·'고객이 직접 보여주는 참고자료'(모집 비주체) 톤 — ConsentGate 하단 안내.

## 범위 밖
- Disclosure 게이트(이미 보유). 라우팅 변경. 산식·계산 lib. 전면 모바일 audit(스크린샷 불가분 점진).

## 자체검증
- /tmp tsc(ConsentGate 단독 + 의존) + 동의 게이트·44px·gating 마커 검증. 스크린샷 불가 시 마커+handoff ⚠.

## 산출
- handoff: 동의 게이트 강화 방식·모바일 변경점·44px 적용 범위. Next: Codex 검증·커밋 → Human 모바일 실기기.
