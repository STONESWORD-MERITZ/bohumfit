# SURIT-029 독립 실손 예상 보험금 계산기
## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows).
## 목적 / 배경
실손 예상 보험금 계산(①청구 가능성 추정 ②실손 자기부담금 상한 ③건보 본인부담상한제)이
현재 알릴의무 분석 결과 화면 안에만 있어, PDF 업로드+분석을 돌려야만 접근 가능하다.
설계사가 분석 없이 실손 청구 실익만 빠르게 확인하도록 독립 진입점을 만든다.
## 범위 (In)
- 설계사 필터(알릴의무 분석 화면) 옆에 "실손 계산" 독립 메뉴/라우트 신설
- 신규 페이지에서 알릴의무 분석 없이 실손 계산만 수행
- 입력 모드 2종(사용자 선택):
  (A) 수기: 급여/비급여 진료비·기관종별·실손 세대(1~5)·소득분위(1~10) 직접 입력
  (B) PDF: 심평원 PDF에서 진료비·기관종별만 추출해 폼 자동 채움(수정 가능),
      알릴의무 Q&A는 실행/표시 안 함
- 기존 실손 계산 로직 재사용(504조합 검증 TS 미러). 산식 재구현 금지.
- 028 동작 유지: 비급여 건별(1회액×횟수) vs 총액 토글, 기관 자동분류+수정
- 결과: 추정 표현만, 면책 문구 표기(기존과 동일)
## 범위 밖 (Out)
- TS 미러 중복 부채 해소(별도 백로그) — 이번엔 "재사용"만, 리팩터링 금지
- Disclosure 화면의 기존 실손 계산 동작 변경 — 불변 유지
- 결과 DB 적재/영구 저장 — 건강정보 비저장 원칙(휘발성)
## 설계 지침 (ENV-MOUNT-NOTES 준수)
- 신규 페이지는 신규 파일(src/pages/InsuranceCalculator.tsx 등) — 마운트 truncation
  위험상 대형 기존파일 편집 최소화
- 계산기 재사용:
  · 이미 독립 컴포넌트면 그대로 import (Disclosure.tsx 무수정)
  · 인라인이면 최소 추출해 공용 컴포넌트화하되, Disclosure.tsx 편집분은 Codex가 Windows 검증
- PDF 모드: 진료비/기관종별 추출이 전체 분석 없이 가능한지 백엔드 확인.
  가능하면 경량 경로, 불가하면 v1은 파싱만 하고 알릴의무 결과 UI 미노출
- 동의/면책: PDF 모드는 기존 민감정보 동의 게이트 동일 적용. 수기 모드는 PDF 동의
  불요하나 동일 면책 문구는 표기
## 검증
- 프런트: npx tsc -p tsconfig.app.json --noEmit / tsconfig.node.json, npm run lint, npm run build
- (백엔드 변경 시) cd backend && python -m pytest -q
- 수동: 신규 라우트 진입 → 수기/PDF 각각 결과 산출, 기존 분석 화면 실손 계산 회귀 없음
- 미러 일치: 신규 페이지 결과 = 기존 분석 화면 = 백엔드 (동일 입력 시 동일 금액)
## 결정 필요 (코드 확인 후 handoff 기록)
- 실손 계산기가 현재 독립 컴포넌트인지 / Disclosure.tsx 인라인인지
- 백엔드에 진료비-only 추출 경로가 있는지, 없으면 추가 여부
- 라우트 경로명 / 네비 항목 명칭

---
## 구현 결과 (Cowork, 2026-06-08) — 결정 3건 답 + 변경
- 결정1: 계산기는 **Disclosure.tsx 인라인** → 신규 `src/lib/insuranceCalc.ts` 로 **verbatim 추출**(산식 재구현 X). 신규 페이지가 import. Disclosure.tsx **무수정**(회귀 0). Disclosure 의 인라인↔lib 중복 제거(lib 단일화)는 **백로그**.
- 결정2: 백엔드 진료비-only 경로 **없음**(`/api/health`·`/api/analyze` 둘뿐). v1 PDF 모드는 **`/api/analyze` 재사용** → 응답 `covered_self_pay_by_year` 로 급여 진료비 자동 채움, **알릴의무 Q&A 미표시**. 경량 parse-only 엔드포인트 추가는 백로그(현재는 분석이 서버에서 실행됨). 기관종별은 per-hospital 데이터 미surface → **자동추출 불가, 수동 입력**.
- 결정3: 라우트 **`/insurance`**, 네비 **"실손 계산"**.
- 변경: `src/lib/insuranceCalc.ts`(신규), `src/pages/InsuranceCalculator.tsx`(신규), `src/App.tsx`(라우트+import), `src/components/Layout.tsx`(네비). Disclosure.tsx·backend 무변경.
