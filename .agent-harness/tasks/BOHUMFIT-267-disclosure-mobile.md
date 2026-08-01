# BOHUMFIT-267 — 고지 결과 모바일 + 266 잔여 표 가독성

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증 PASS·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex).
Date: 2026-08-01 · 기준 HEAD `9eef3cf`(266)

## ★제1원칙 — 데스크톱 회귀 0
266 방식 준수: CSS 숨김이 아니라 `useIsMobile` JS 분기(matchMedia 부재 시 데스크톱 폴백).
검증은 266 선례대로 **HEAD 사본 대비 데스크톱 렌더 `innerHTML`·노드 수 동일**로 증명한다.

## STEP 0 실측 (2026-08-01)

### Disclosure 현행 구조 (`Disclosure.tsx` 2,211줄)
| 요소 | 위치 | 역할 |
|---|---|---|
| `DiseaseCard` | 392~ | 질병명 + Q배지 + 진료기간/입원회차/최초진단 + 칩(입원·통원·수술·투약) + **근거 상세 아코디언**(251 수술 건별 포함) |
| `DisclosureSection` | 604~ | **카톡 문안**(`visibleMemo`) + 복사 + 결과 조회기간 필터 + Q별 섹션 → `DiseaseCard` 목록 |
| 호출부 | 1449 | 탭 패널에서 `reports`·`memo`·`referenceDate`·`unassignedSurgeries` 전달 |
- 문안 생성 = `buildFilteredDisclosureMemo`(기간 필터 시) 또는 `withDisclosureSelectionHeader`(전체).
  ★모바일도 **같은 `visibleMemo` 문자열**을 그대로 쓴다 — 재구성 0(251 골든 픽스처 동등성 유지).

### ★전제 반전 1 — 배지 4단 매핑은 오표기를 만든다
실제 판정 체계는 **Q1~Q5 5종**이다: Q1 3개월 / Q2 1년(건강체)·10년(간편) / Q3 5년 /
Q4 5년 초과 10년 / Q5 5년 중대질병(`Disclosure.tsx:410~412` 실측).
265 `DisclosureBadge`는 **4단**(고지대상·10년 / 고지대상·3개월 / 검토·1년 재검사 / 해당없음)이고,
시안 원본은 그마저 "고지대상 · **5년**"으로 쓴다(시안 실측 — 265 Human 확정 "10년"과도 다르다).
→ Q3(5년)를 "고지대상·10년"으로 찍으면 **고객에게 잘못된 기간을 안내**하게 된다. 고지 판정은 이 서비스의
핵심 산출물이라 임의 매핑은 실무 리스크다.
**결정: 모바일 배지도 현행 Q 판정·기간 라벨을 그대로 쓴다**(정보 손실·오표기 0). 265 토큰의 **시각 스타일**
(상태 면·15px·radius 8)만 차용하고, `DisclosureBadge` 4단 컴포넌트는 이번에 쓰지 않는다.
※4단으로 통합할지, Q별 5종을 유지할지는 **Human 결정 사항**으로 올린다(아래 "Human 보고").

### ★전제 반전 2 — 질병 카드를 새로 그리면 251 정보가 샌다
`DiseaseCard`는 이미 "카드 + 배지 + 요약 칩 + 아코디언" 구조이고, 그 안에 **251의 수술 건별 전개
(날짜/원문코드/맥락/병명/수술명)·동일일자 복수코드·미특정 블록**이 들어 있다. 모바일용으로 다시 그리면
누락 위험이 실재한다(명세도 "정보 누락 0"을 요구).
**결정: 질병 카드는 기존 `DiseaseCard`를 그대로 렌더한다.** 모바일에서 새로 만드는 것은
①헤더 요약 ②카톡 문안 BottomSheet ③하단 고정 주 액션 — 즉 **카드를 감싸는 껍데기**만이다.
이러면 정보 동등성이 "테스트로 확인"이 아니라 **구조적으로 보장**된다.

## 구현
### P1 — 고지 결과 모바일 (`src/components/mobile/DisclosureMobileShell.tsx`)
1. **헤더 요약**: 질병 그룹 수·Q별 판정 집계 배지·기준일·선택 조회기간(+ 고객명·나이·서류 건수는
   호출부가 넘길 때만 표시 — 없으면 생략).
2. **질병 카드**: 기존 `DiseaseCard`(children으로 그대로 받는다) — 정보 누락 0.
3. **카톡 문안**: 265 `BottomSheet`로 전문 표시 + 복사. 복사 성공 시 `showUndoToast` scope `copy-done`
   (265 허용 3곳 중 하나). ★문안 문자열은 `visibleMemo` 그대로.
4. **주 액션**: 265 `PrimaryAction` 56px 하단 고정("카카오톡 문안 보기").

### P2 — 266 잔여 표 가독성 (`src/components/mobile/CoverageInsightMobile.tsx`)
- 종합비교(560px 표) → **항목 리스트**(항목 · 전 → 후 · 개선), 15px 이상·가로 스크롤 0.
- Y/N(420px 표) → **배지 리스트**(항목별 전/후 Y·N).
- `CoverageInsightBlocks.tsx`에서 `useIsMobile` 분기 — 데스크톱 표는 무변경.

## 수정 금지
backend 무접촉 · 고지 판정/문안 생성 로직 변경 0(251 4경로·골든 픽스처 무접촉) · 집계/파서 변경 0 ·
데스크톱 렌더 경로 변경 0 · 시안 파일 레포 이동 금지.

## ★Human 보고 (이번 범위에서 처리하지 않음)
1. **고지 배지 체계** — 265 4단 vs 현행 Q1~Q5 5종. 4단으로 통합하면 Q2/Q4/Q5의 기간이 사라지거나
   잘못 표기된다. 통합 여부·매핑 규칙은 판정 정책이라 Human 확정이 필요하다.
2. **`DiseaseCard` 폰트 하한** — 263이 지적한 소형 폰트 70건이 이 카드에 몰려 있다(11~13px).
   265 하한(15px)에 맞추려면 **데스크톱 표시도 함께 바뀌므로** 제1원칙과 충돌한다. 별도 태스크 필요.

## 검증 결과 (1차 · 2026-08-01 · Windows 로컬)

- [x] ★**데스크톱 회귀 0 — HEAD 사본 대비 실렌더 4건**(266 선례 방식). `git show HEAD:...`로 265→266 시점
      사본 3종(`Disclosure`·`CoverageRemodel`·`CoverageInsightBlocks`)을 꺼내 같은 동선을 태우고
      `innerHTML`·노드 수를 대조 — **전부 완전 일치**:
      ①`Disclosure` 결과 화면(업로드→분석→카톡 문안·질병 카드까지) ②`CoverageRemodel` 결과 화면
      ③`StageComparisonTable` ④`YnFlagTable`. 빈 화면 오통과 방지로 노드 수 하한과 실제 마커
      (`등통증`·`복사하기`·`결과 조회기간`·`⑤` 섹션·`min-w-[560px]`·`min-w-[420px]`)를 함께 단언했다.
      ※사본·일회성 스크립트는 검증 후 **삭제**(레포 잔재 0).
- [x] ★**정보 동등성** — 질병 카드는 기존 `DiseaseCard`를 children으로 통과시키므로 구조적으로 보장된다.
      테스트로 251 수술 상세(원문코드·수술명)가 셸을 거쳐도 손상되지 않음을 고정했다.
- [x] ★**카톡 문안 문자열 동등성** — 시트에 표시되는 문자열이 호출부 `visibleMemo`와 **완전 일치**(`toBe`),
      복사 시 클립보드에 같은 문자열이 들어가고 되돌리기가 이전 클립보드를 복원한다.
      되돌리기 scope는 265 허용 3곳 중 `copy-done`임을 상수로 확인.
- [x] 헤더 요약 — 총 건수(질문별 합)·질문별 집계(★Q 번호 유지)·기준일·조회기간·고객명/서류 건수(optional).
      집계는 섹션 렌더와 **같은 기간 필터**를 써서 건수가 어긋나지 않는다.
- [x] P2 — 종합비교·Y/N 모바일 리스트가 데스크톱 표와 **같은 값·순서·증감 산식**을 쓰고,
      `table`·`overflow-x`·`min-w-[` **0건**, 폰트 **15px 이상**(테스트로 스캔).
- [x] `npm test` **203 passed / 26 files**(190 + 13) · tsc app/node · lint 클린
- [x] backend `pytest -q` **792 passed, 8 skipped** · ★**`backend/` diff 0**
- [x] 라우트 스모크 **18/18** · `npm run smoke:coverage` **PASS** · PII 0
- [x] `build:verify` **343,225 B** — 264~266과 동일 수치 예상 FAIL(248 로컬 껍데기 · 이번 변경과 무관)
- [x] diff 범위 = `src/pages/Disclosure.tsx`(+48/-4) · `src/components/CoverageInsightBlocks.tsx`(+12) ·
      `src/components/mobile/` 신규 2 + 테스트 1 + harness. backend·판정/문안 생성·집계/파서 diff 0.

### 자체 정정 1건
265의 "5년 잔재 0" 가드가 **내가 새로 쓴 주석**을 잡아 `npm test`가 1건 실패했다(가드가 의도대로 동작).
배지 매핑 위험을 설명하며 기간 숫자를 예시로 든 부분을 "다른 기간으로 잘못 표기"로 바꾸고,
질문별 실제 기간의 정본이 `Disclosure.tsx`의 `windowLabels`임을 가리키도록 고쳤다.

### 로컬에서 못 한 것 (Codex 몫)
- **375/390/430px 실렌더 넘침 측정** — jsdom은 레이아웃을 계산하지 않는다. 구조적 근거(모바일 경로에
  고정폭 표·가로 스크롤 컨테이너 0)까지만 고정했고 **실측은 프로덕션 브라우저**에서 263 방식으로 필요.
- 실기기에서 바텀시트 조작감·하단 고정 액션이 카드 마지막 줄을 가리지 않는지는 Human 실사용 확인 대상.

## Codex 2차 검증 (2026-08-01 · PASS)

- Windows 전체 게이트: backend **792 passed, 8 skipped** · frontend **203 passed / 26 files** ·
  tsc app/node · lint · 라우트 **18/18** · `smoke:coverage` 정본 2건 PASS.
- 251 문안 골든은 pytest **14/14**·vitest **14/14**로 서버/필터/analyzer/`disclosureMemo` 문자 단위 동등성을
  재현했다. 문안 생성부·공유 골든·`CoverageRemodel` diff는 모두 0이다.
- 별도 worktree의 HEAD `9eef3cf`와 같은 픽스처를 렌더해 데스크톱 4건의 `innerHTML` SHA-256·노드 수를
  완전 대조했다: Disclosure **86d0266b…b560 / 99**, CoverageRemodel **3bfdf964…a44f / 442**,
  종합비교 **ec137641…5c70 / 58**, Y/N **a3a8b8cc…5574 / 24**. 임시 테스트·worktree는 삭제했다.
- 실제 CSS 렌더로 **375/390/430px 모두 가로 넘침 0**, 신규 모바일 글자 하한 **15px**, 상세 조작
  **44px**, 주 액션 **56px**, 문안 시트 overflow 0·문자열 완전 일치를 확인했다. 바텀시트 핸들은 시각 4px,
  `::before` 히트영역이 **44×44px**라 터치 계약을 충족한다. 일회성 렌더 하네스는 삭제했다.
- `npm run build`는 성공했으나 **343,225 B** 껍데기이며 `build:verify`가 계약대로 exit 1로 거부했다.
  범위는 선언 8파일뿐이고 backend/pipeline/coverage/public/SW/package/lock/supabase·PII·구브랜드 diff 0,
  `git diff --check` clean이다.

## Stage 목록 (Codex용)
`src/pages/Disclosure.tsx`, `src/components/CoverageInsightBlocks.tsx`, `src/components/mobile/*`(신규 2),
테스트, `tasks/BOHUMFIT-267-disclosure-mobile.md`, `handoff.md`, `locks.md`

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-267): 고지 결과 모바일 뷰 + 모바일 표 가독성(종합비교·Y/N)

## Next
① **Codex** — 2차 검증(데스크톱 회귀 0·문안 동등성·브라우저 실렌더·배포 스모크) → 커밋·push
② **Human** — 폰에서 고지 결과 실사용 + 위 Human 보고 2건 결정
③ **Chat** — 268(업로드·분석 진행) → 269(홈·네비) 발번
