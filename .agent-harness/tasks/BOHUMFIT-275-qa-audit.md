# BOHUMFIT-275 — 263~273 누적 QA 교차 감사

Owner flow: Claude Chat -> Codex(조사·문서) -> Human/Chat(후속 결정)
Risk tier: 조사 전용 — ★제품 코드 변경 0 · git 쓰기 0
Date: 2026-08-07 · 감사 착수 HEAD `3201528`, 완료 시 관찰한 로컬 HEAD `d95e56b`

## 0. 범위·방법·제약

- 루트 게이트: `C:\Users\18_rk\BOHUMFIT`, remote `STONESWORD-MERITZ/bohumfit`, 리트머스
  `.agent-harness/tasks/BOHUMFIT-219-shared-rls-migration-alignment.md` 존재를 확인했다.
- 정적 전수 검색과 호출 경로 추적을 사용했다. `fixed`/`sticky`, z-index, safe-area, `useIsMobile`,
  반응형 숨김 클래스, 브라우저 저장소, 로그, 파일명·고객명·상병코드·기관명, 263~273 task/handoff,
  262 결정지를 대조했다.
- 착수 시점에 276a·276b 미커밋 변경이 이미 존재했다. 이 파일들은 읽기만 했고 한 줄도 수정하지 않았다.
  감사 도중 별도 프로세스가 이를 `f254e8c`·`d95e56b`로 커밋해 로컬 HEAD가 이동했다. 275는 해당
  커밋·제품 파일에 관여하지 않았으며, 완료 시점 `git status`의 제품 코드 diff는 0이다.
- 실 PDF·엑셀·PII는 열지 않았고 임시 렌더 산출물도 만들지 않았다. 프로덕션·실기기·브라우저 세션은
  사용하지 않았다. 실행 상태가 필요한 항목은 아래에 **확인 불가**와 이유를 명시했다.
- 제품 코드 변경이 없는 정적 감사이므로 pytest/npm 게이트는 재실행하지 않았다. 이 태스크의 검증 계약인
  문서 범위·제품 코드 diff 0·산출물 미저장을 읽기 전용 git 상태와 파일 검색으로 확인했다.

## 1. 요약 판정

| ID | 발견 | 심각도 | 판정 |
| --- | --- | --- | --- |
| A-1 | 고지 업로드의 구형 하단 CTA가 모바일 하단 네비와 같은 화면에서 겹침 | **실사용 결함** | 273 외 잔여 충돌 |
| A-2 | 설치·업데이트 안내와 토스트가 하단 네비/액션/오버레이를 모르는 전역 fixed 요소 | 잠재 위험 | 동시 노출 조정자 없음 |
| B-1 | 원본 파일명이 서버 로그 및 raw `parse_errors`에 남고, 히스토리에 raw 결과가 저장될 수 있음 | **실사용 결함** | 화면 익명화만으로 저장·로그 경로 미차단 |
| B-2 | 10분 재보기 `sessionStorage`가 로그아웃 시 미삭제·사용자 소유권 미검사 | **실사용 결함** | 같은 탭 계정 전환 시 이전 결과 복원 가능 |
| B-3 | 5건/24시간 IndexedDB 캐시는 구현 파일만 있고 저장·조회 호출부가 0 | **실사용 결함** | 방침·동의 문구와 실제 동작 불일치 |
| B-4 | 미매핑 오류 원문을 브라우저 콘솔에 남기며 프런트 Sentry 필터가 breadcrumb/exception 문자열을 정제하지 않음 | 잠재 위험 | 운영 전송 실측은 확인 불가 |
| C-1 | 구형 `md:hidden` 고정 CTA가 JS 모바일 분기와 공존 | 잠재 위험 | 제1원칙 위반·A-1 원인 |
| D-1 | 265 하한 가드가 `src/components/mobile/` 및 숫자형 px만 검사해 실제 모바일 11~14px를 놓침 | **실사용 결함** | 가드 PASS와 런타임 하한 준수가 다름 |
| E-1 | `verify.md` overview 정본 설명이 259 이후에도 "회사 열 미생성"으로 남음 | 정리 필요 | 현재 코드·스모크 정본과 모순 |
| E-2 | 264~273 task 머리말의 owner/미커밋 안내가 다수 과거 상태 | 정리 필요 | handoff·git log에는 완료 해시 존재 |

## A. 하단 고정 요소 전수

### A-0. 요소 목록

| 요소 | 위치 | z-index / DOM 순서 | safe-area | 동시에 나타나는 범위·판정 |
| --- | --- | --- | --- | --- |
| 모바일 하단 네비 | `src/components/mobile/MobileBottomNav.tsx:41-50` | `z-40`; `Layout`의 main·Footer 뒤(`src/components/Layout.tsx:326-330`) | 자체 `paddingBottom: env(safe-area-inset-bottom)` | 로그인 모바일 전 경로. `aria-modal=true` dialog 또는 `data-analysis-busy`가 있으면 미렌더 |
| 모바일 결과 주 액션 | `src/components/mobile/PrimaryAction.tsx:91-128` | `z-40`; main 안이라 네비보다 DOM 앞 | 네비가 있으면 실측 높이만큼 `bottom` 이동하고 12px, 없으면 `.m-action-bar`가 safe-area 포함 | 고지 결과. 273 수정 경로는 겹침 0으로 설계됨 |
| 구형 고지 분석 CTA | `src/pages/Disclosure.tsx:1876-1881,2352-2364` | `z-50`, `bottom-0`; main 안·네비보다 앞이지만 z가 큼 | **없음** | 스크롤 `>240px`·분석 결과 없음. 로그인 모바일 네비와 공존하고 위에서 덮음 |
| 설치 안내 | `src/components/InstallPrompt.tsx:42-70` | `z-50`; `<App/>` 뒤 전역 형제(`src/main.tsx:33-40`) | `marginBottom: env(safe-area-inset-bottom)` | 설치 가능/iOS 안내 상태에서 모든 화면과 공존. `role=dialog`이나 `aria-modal`이 없어 네비 observer가 감지하지 않음 |
| SW 업데이트 안내 | `src/components/mobile/UpdatePrompt.tsx:13-27` | `z-[9997]`, `bottom-0`; `<App/>` 뒤 전역 형제 | 자체 bottom padding에 safe-area 포함 | waiting worker가 있으면 모든 화면과 공존. `role=status`라 네비 observer가 감지하지 않음 |
| 토스트 컨테이너 | `src/components/ToastContext.tsx:52-59`, `src/components/Toast.tsx:51-56` | `z-[9999]`, `bottom-4 right-4`; App 내부 마지막 | **없음** | 모든 화면. 컨테이너는 pointer-events-none이나 개별 toast는 pointer-events-auto |
| 모바일 업로드/문안 BottomSheet | `src/components/mobile/BottomSheet.tsx:66-100` | `z-[9998]`, full-screen | `.m-sheet`가 safe-area + gutter(`src/index.css:369-372`) | `role=dialog aria-modal=true`; 네비 숨김. 문안 시트가 열리면 고정 PrimaryAction도 숨김 |
| 보장분석 전체표 | `src/components/mobile/CoverageMobileView.tsx:257-281` | `z-[9990]`, full-screen | 스크롤 영역 bottom safe-area | `aria-modal=true`; 네비 숨김 |
| 고지 저장/튜토리얼·히스토리 모달 | `src/pages/Disclosure.tsx:1613-1618,1792-1807`, `src/pages/History.tsx:452-519` | `z-50` 또는 `z-[1000]`, full-screen | 별도 하단 safe-area 없음 | 모두 `aria-modal=true`; 네비 숨김 |

`sticky` 전수에서 하단 고정은 없었다. `Layout` 헤더와 일부 표의 첫 열만 top/left sticky다
(`src/components/Layout.tsx:233`, `src/components/mobile/CoverageMobileView.tsx:281,293`).

### A-1. 동시 노출 조합 전수

| 화면/상태 | 동시 요소 | 판정 | 근거·재현 조건 |
| --- | --- | --- | --- |
| 로그인 모바일 고지 업로드, 240px 초과 스크롤 | 구형 CTA + 하단 네비 | **겹침 확정(실사용 결함)** | 둘 다 `bottom-0`; CTA `z-50` > 네비 `z-40`. 구형 CTA는 `isMobile` JS 분기 밖이며 `md:hidden`만 사용. CTA 버튼은 새 시트를 열지 않고 `analyze`를 직접 호출(`Disclosure.tsx:2357`) |
| 고지 분석 중 | 구형 CTA + 분석 busy; 네비는 숨김 | 네비 충돌은 없음, 구형 CTA 잔존 | `!result`라 loading 중에도 CTA가 남고 disabled만 됨. `AnalysisProgress`의 `data-analysis-busy`가 네비를 숨김(`AnalysisProgress.tsx:15-16`) |
| 고지 결과 | PrimaryAction + 하단 네비 | **273으로 해소** | PrimaryAction이 네비 실제 높이를 Mutation/ResizeObserver로 측정해 위에 쌓임(`PrimaryAction.tsx:27-61,113-124`) |
| 업로드/문안 시트·저장 모달·튜토리얼·전체표 | modal + 네비 | **네비 충돌 없음** | `MobileBottomNav.tsx:23-33`가 `role=dialog[aria-modal=true]`를 감지해 미렌더 |
| 모든 모바일 화면 + 설치 안내 | InstallPrompt + 네비 또는 PrimaryAction | **잠재 겹침** | 설치 안내는 bottom-3 z50이고 observer 대상이 아님. 고지 결과에선 z50이 action/nav z40 위에 옴 |
| 모든 화면 + 업데이트 안내 | UpdatePrompt + 네비/PrimaryAction/전체표/튜토리얼 | **잠재 겹침** | bottom-0 z9997이며 observer 대상이 아님. 전체표 z9990·튜토리얼 z1000보다도 높음 |
| 모든 화면 + 토스트 | Toast + 하단 fixed 요소 | **잠재 가림/히트 충돌** | bottom-4 z9999, 개별 toast가 pointer-events-auto. 되돌리기 토스트는 6초라 액션/네비와 동시에 조작될 수 있음 |
| BottomSheet + UpdatePrompt + Toast | z9998 + z9997 + z9999 | Sheet 위에는 toast, 뒤에는 update | z 순서상 결정됨. 사용자가 동시에 보는 실제 화면은 waiting worker/토스트 상태가 필요 |
| z50 모달 + InstallPrompt | 둘 다 z50, InstallPrompt가 App 뒤 | **잠재 모달 가림** | 같은 stacking context라면 뒤 DOM인 전역 InstallPrompt가 위에 올 수 있음 |

**확인 불가:** iOS safe-area 34px, 실제 설치 이벤트, waiting worker, 토스트가 동시에 생긴 실기기 좌표 히트
테스트는 이번 조사에서 브라우저·실기기를 사용하지 않아 실행하지 못했다. 다만 A-1의 구형 CTA/네비는 동일
`bottom-0`과 z-index가 정적으로 확정돼 런타임 조건만 충족하면 겹친다.

### A 발견 사항

#### A-F1 — 구형 분석 CTA와 하단 네비 충돌

- 위치: `src/pages/Disclosure.tsx:1876-1881,2352-2364`, `src/components/mobile/MobileBottomNav.tsx:41-50`
- 증상/위험: 로그인 모바일에서 240px 이상 스크롤하면 구형 CTA가 네비 위를 덮는다. 268a의 업로드
  시트 동선과 별개로 `analyze`를 직접 호출해 모바일 동선도 이원화한다.
- 심각도: **실사용 결함**
- 재현 조건: `/disclosure` 로그인 모바일, 결과 없음, 스크롤 >240px.
- 수정 방향 제안(구현 금지): 구형 CTA를 모바일 JS 분기에서 제거하거나 새 업로드 시트 열기 동선으로
  단일화하고, 전역 bottom-surface 조정자를 둔다.

#### A-F2 — 전역 설치/업데이트/토스트의 충돌 회피 계약 부재

- 위치: `src/main.tsx:33-40`, `src/components/InstallPrompt.tsx:65-70`,
  `src/components/mobile/UpdatePrompt.tsx:17-27`, `src/components/ToastContext.tsx:52-59`
- 증상/위험: 세 요소가 네비·PrimaryAction·modal의 존재를 모르며 z-index도 50/9997/9999로 분산돼 있다.
- 심각도: 잠재 위험
- 재현 조건: 설치 가능 또는 waiting worker 상태 + 로그인 모바일; toast는 사용자 액션을 추가.
- 수정 방향 제안(구현 금지): 단일 overlay/bottom-surface 레지스트리와 z-index 토큰을 두고, 네비/액션이
  관찰할 공통 상태·ARIA 계약을 정의한다.

## B. PII 노출·저장 전수

### B-0. 경로별 현행

| 경로 | 노출/저장 값 | 현행 판정·근거 |
| --- | --- | --- |
| 고지 결과 화면 | 고객명, 상병코드·병명, 기관명, 진료/수술 근거 | 인증 결과 화면의 핵심 정보로 의도 노출. `Disclosure.tsx:440-520,1456-1520`; 모바일은 동일 DiseaseCard children을 재사용 |
| 보장분석 화면 | 고객명은 마스킹(`CoverageRemodel.tsx:767-770`), 계약/회사/상품/담보 정보 표시 | 의도 노출. 업로드 직후 원본 파일명도 `CoverageRemodel.tsx:388,674`에서 표시 |
| 업로드 UI | 선택한 원본 파일명 목록 | `Disclosure.tsx:1875,1909,2275-2301`, `MobileUploadSheet.tsx:153-160`. 현재 세션 사용자에게만 보이는 선택 확인 정보 |
| 고지 PDF | 고객명·상병코드·기관명·진료/수술 근거 | 사용자 요청 출력. `backend/templates/report_disclosure.html:200,245-271`; 화면에도 개인정보 포함 경고(`Disclosure.tsx:1519`) |
| 보장 엑셀/PDF | 고객명·계약/회사/담보 | 엑셀 표지는 원문 고객명(`backend/coverage/export_excel.py:241-270`), PDF는 이름 마스킹(`export_pdf.py:143-146`). 두 출력의 이름 정책이 서로 다름 |
| 카카오 복사문 | 상병코드·병명·기관명·수술 사건 | 사용자 클릭으로 clipboard에 기록. 서버 `_kakao_item`(`backend/main.py:420-570`)과 프런트 memo 경로, 모바일은 가공 없이 복사(`DisclosureMobileShell.tsx:92-149`) |
| 고지 parse 오류 화면 | 원본 대신 `서류 N` | 화면 직전 `sanitizeParseErrors` 적용(`Disclosure.tsx:1456-1462`, `errorMessages.ts:136-163`) |
| 분석 티커 | `서류 N`, 레코드/유형/오류 건수 | 원본 파일명·환자명·코드·병명 없음. `backend/progress.py:65-84,100-121`; 메모리 15분/200작업 상한 |
| 브라우저 일반 오류 | 사전 문구 또는 폴백 | 화면은 정제. 미매핑 원문은 `console.warn`에 남음(`errorMessages.ts:121-133`) |
| 서버 로그 | **원본 파일명**, 예외 문자열 | 성공도 `file=%s`(`backend/analyzer.py:243-248`), 순차/병렬 실패도 원본명(`:281-283,315-319`) |
| Supabase recent/saved history | 분석 결과 전체에서 최상위 `customer_name`만 제거 | 7일/90일 저장. shallow copy 후 `customer_name`만 pop(`backend/main.py:1505-1527,1559-1564`) |
| `sessionStorage` | **전체 AnalyzeResult**(고객명·코드·기관명·raw parse_errors 포함 가능), 10분 | `bohumfit_result`; 소유자 id 없음(`Disclosure.tsx:1962-1976,2097,2139`) |
| IndexedDB | 설계상 payload 5건/24h/userId | 모듈은 있으나 `saveAnalysis/listAnalyses/getAnalysis`의 제품 호출부 **0건**. 로그아웃은 `clearAnalysisCache`만 호출(`analysisCache.ts:98-155`, `AuthContext.tsx:32-45,74-88`) |
| localStorage | 설치 안내 닫힘 시각, 투어 확인 | 검색 결과 건강정보 저장 없음(`pwa.ts:103-115`, `Disclosure.tsx:155-169`) |
| 서버 요청 메모리 | 업로드 PDF bytes·파싱 결과, 분석 진행 메모리 | 요청 처리 중 존재. 파일 영구 쓰기 경로는 확인되지 않음. 실제 프로세스 메모리 회수 시점은 확인 불가 |
| 알림 | 없음 | `public/sw.js`/제품 코드에 push·`notificationclick`·`showNotification` 구현 0. 268c 미착수 |

### B-F1 — raw parse_errors 파일명이 히스토리에 저장될 수 있음

- 위치: `backend/pipeline/pdf_parser.py:368-384`, `backend/main.py:1505-1527,1559-1564,2265-2268`,
  `src/lib/errorMessages.ts:136-163`
- 증상/위험: 271은 **표시 직전만** 파일명을 지운다. 서버 응답의 raw `parse_errors`에는 원본 파일명이
  남고, recent/saved 저장은 최상위 `customer_name`만 제거하므로 파일명 속 실명이 DB에 7일/90일
  저장될 수 있다. 271 주석에도 실명 포함 파일명 실측이 명시돼 있다.
- 심각도: **실사용 결함**
- 재현 조건: 파일명에 고객명이 있고 해당 PDF가 비밀번호/손상/빈 결과 등 parse error를 생성한 분석.
- 수정 방향 제안(구현 금지): 서버 응답·로그·history 저장 전에 파일 식별자를 익명 slot으로 정규화하고,
  화면용 sanitization을 방어 2선으로 남긴다. 기존 DB raw 결과 정리 범위는 Human 데이터 정책 결정 필요.

### B-F2 — 성공/실패 파싱 로그에 원본 파일명 기록

- 위치: `backend/analyzer.py:243-248,266-267,281-283,315-319`
- 증상/위험: 정상 분석마다 원본 파일명이 Railway 로그에 남는다. 파일명에 환자명이 들어갈 수 있다는
  268b 원칙과 정면 충돌한다.
- 심각도: **실사용 결함**
- 재현 조건: 이름 포함 파일 업로드(성공·실패 모두).
- 수정 방향 제안(구현 금지): 로그도 `서류 N`/파일 index만 기록하고 exception 문자열을 별도 PII
  scrubber로 통과시킨다.

### B-F3 — sessionStorage 계정 전환 누수

- 위치: `src/pages/Disclosure.tsx:1962-1976,2097,2139,2415`, `src/lib/AuthContext.tsx:32-45`
- 증상/위험: 전체 결과를 10분 보관하지만 로그아웃 구독은 IndexedDB만 지운다. 저장 레코드에 user id가
  없고 복원 시 현재 사용자와 대조하지 않는다. 같은 탭에서 A가 분석→로그아웃→10분 내 B가 로그인해
  `/disclosure`에 진입하면 A 결과를 복원할 수 있다.
- 심각도: **실사용 결함**
- 재현 조건: 동일 브라우저 탭, 10분 이내 계정 전환.
- 수정 방향 제안(구현 금지): AuthContext의 단일 정리 지점에서 이 키도 삭제하고, 저장 레코드에 user id를
  넣어 복원 시 이중 대조한다.

### B-F4 — 265 오프라인 캐시가 실제 동선에 배선되지 않음

- 위치: `src/lib/analysisCache.ts:98-155`, `src/pages/PrivacyPolicy.tsx:46-54`,
  `src/components/ConsentGate.tsx:37-47`
- 증상/위험: 제품 코드 검색상 `saveAnalysis`, `listAnalyses`, `getAnalysis` 호출부가 정의부 밖에 0건이다.
  실제 분석 결과는 IndexedDB에 저장/복원되지 않는데 방침·동의문은 최근 5건이 24시간 임시 보관된다고
  단정한다. 반대로 실제 `sessionStorage` 10분 저장은 해당 문구에 없다.
- 심각도: **실사용 결함**(기능·고지 불일치)
- 재현 조건: 분석 완료 후 오프라인 열람 또는 IndexedDB `bohumfit-offline/analyses` 확인.
- 수정 방향 제안(구현 금지): Human이 A안 유지/철회부터 재확정한 뒤, 유지면 저장·목록·복원 동선을
  user-bound로 배선하고 모든 저장소를 한 정리 계약에 포함한다. 철회면 방침·동의문을 실제 동작에 맞춘다.

### B-F5 — 콘솔/Sentry 원문 가능성

- 위치: `src/lib/errorMessages.ts:129-132`, `src/main.tsx:13-27`, `backend/main.py:135-173`
- 증상/위험: 프런트는 미매핑 raw 오류를 콘솔에 남기고, `beforeSend`는 request data/cookies만 지운다.
  console breadcrumb나 exception 문자열의 파일명/건강정보를 별도 scrub하지 않는다. 백엔드 scrubber도
  키 기반이라 이미 포맷된 로그 문자열의 원본명이 남을 가능성이 있다.
- 심각도: 잠재 위험
- 재현 조건: 원본 파일명/의료정보를 포함한 미매핑 오류 + Sentry 활성 환경.
- 수정 방향 제안(구현 금지): 프런트·백엔드 모두 구조화 로그 whitelist와 최종 문자열 scrub을 적용한다.
- **확인 불가:** 실제 프로덕션 Sentry 이벤트·Railway 로그 보존 내용과 전송 여부는 접근하지 않아 확인하지 못했다.

### B-1. 현재 PII 기준의 일관성 판정

중앙화된 단일 기준은 없다. 코드 주석에서 추론 가능한 현재 의도는 다음과 같다.

1. 인증된 분석 결과 화면과 사용자가 명시적으로 생성/복사한 PDF·엑셀·카카오 문안에는 상병코드·병명·기관명과
   고객 식별 정보가 필요 범위에서 노출될 수 있다.
2. 진행 표시·오류·최근 목록·로그 같은 **부수 경로**에는 원본 파일명·실명을 두지 않는다.
3. 서버 히스토리는 고객명만 제거하고 건강정보 결과 자체는 7일/90일 보관한다.

그러나 성공 로그의 원본 파일명, raw parse_errors의 히스토리 저장, 선택 파일명/보장분석 경고 표시,
sessionStorage, 미배선 IndexedDB가 서로 다른 기준을 사용한다. 따라서 "노출돼도 되는 것/안 되는 것" 기준은
**현재 일관되지 않다**. 별도 PII 데이터 분류표(표시·일시 메모리·기기 저장·서버 저장·운영 로그·외부 전송)를
정본으로 만드는 후속이 필요하다.

### B-2. 265 IndexedDB 삭제 5경로 추적

| 경로 | 단일 삭제 지점 도달 근거 | 판정 |
| --- | --- | --- |
| 수동 버튼·PhoneVerify | 공용 `signOut()` 호출(`Layout.tsx:181`, `PhoneVerify.tsx:98`) → auth 사용자 id가 `id→null` | IndexedDB 전량 삭제 경로 존재 |
| 30분 무활동 | `AuthContext.tsx:57-63`의 직접 Supabase signOut → 같은 auth 구독 | IndexedDB 전량 삭제 경로 존재 |
| ResetPassword 직접 종료 | `ResetPassword.tsx:75`의 직접 Supabase signOut → 같은 auth 구독 | IndexedDB 전량 삭제 경로 존재 |
| 세션 만료·갱신 실패 | 앱 호출과 무관하게 auth session이 `id→null` | IndexedDB 전량 삭제 경로 존재 |
| 다른 탭 로그아웃·계정 전환 | auth session이 `id→null` 또는 `id→다른 id` | IndexedDB 전량 삭제 경로 존재 |

- 실제 삭제 호출은 이벤트명이 아니라 `prevUserId !== nextUserId`인 한 지점
  (`AuthContext.tsx:32-45`)에 있고, 같은 id의 토큰 갱신은 삭제하지 않는다. 카카오 외부 이탈만 구독의
  비동기 작업 중단을 막기 위해 redirect 직전 멱등 flush가 있다(`:74-88`). 합성 auth 이벤트 검증은
  `authCacheClear.test.tsx:67-126`에 있다.
- **판정:** 정의된 IndexedDB 스토어에 대해서는 5경로가 한 삭제 계약으로 연결된다. 그러나 B-F4처럼 현재
  저장 호출 자체가 0이고, B-F3의 `sessionStorage`는 이 삭제 계약 밖이다. 따라서 "분석 관련 기기 저장소가
  전 경로에서 모두 삭제된다"는 더 넓은 명제는 **거짓**이다.
- **확인 불가:** 실제 다른 탭·세션 만료·카카오 이탈 중 IndexedDB 삭제 완료는 브라우저 세션을 사용하지 않아
  실측하지 못했다. 삭제 오류도 `.catch(() => {})`로 사용자에게 드러나지 않는다.

## C. 모바일 분기 일관성

### C-0. `useIsMobile` 전수

공통 훅은 `src/components/mobile/useIsMobile.ts:13-45` 한 곳이며, SSR/`matchMedia` 부재·예외 모두
`false`(데스크톱)로 폴백한다. 모든 사용처가 이 훅을 공유하므로 **matchMedia 부재 폴백은 전 사용처에 존재**한다.

| 파일·행 | 호출 수 | 용도 | 판정 |
| --- | ---: | --- | --- |
| `src/App.tsx:60-69` | 1 | 로그인 후 모바일 `/dashboard`, 데스크톱 `/disclosure` | 의도된 동작 분기 |
| `src/components/Layout.tsx:187-194` | 1 | 로그인 모바일 하단 네비 | 의도된 구조 분기 |
| `src/pages/Disclosure.tsx:440-441,711-852,1888-2330` | 3 | 폰트 맵, 결과 셸, 업로드 XHR/시트 | JS 단일 렌더 원칙 준수 |
| `src/components/AnalysisProgress.tsx:10-23` | 1 | 모바일 티커만 추가 | 의도된 부가 표시 |
| `src/pages/Dashboard.tsx:116-139` | 1 | 모바일 홈 | JS 단일 렌더 원칙 준수 |
| `src/pages/CoverageRemodel.tsx:284,831-1470` | 1 | 모바일 계약/요약/전체표 | JS 단일 렌더 원칙 준수 |
| `src/components/CoverageInsightBlocks.tsx:30-31,90-91` | 2 | 종합비교/Y/N 모바일 리스트 | JS 단일 렌더 원칙 준수 |

합계 **7파일·10호출**이다.

### C-1. CSS 숨김 분기

- **기능 분기 잔여:** `src/pages/Disclosure.tsx:2352-2364`의 구형 분석 CTA가 `md:hidden`으로만
  모바일 분기된다. JS 모바일 업로드 시트와 DOM에 동시에 존재하며 A-F1을 만든다. 제1원칙 위반.
- **전역 내비 구조 분기:** `src/components/Layout.tsx:242-280`은 데스크톱 nav/user와 모바일 햄버거를
  `hidden lg:flex`, `hidden lg:block`, `lg:hidden`으로 나눈다. 269b 하단 네비는 JS 분기라 로그인 모바일에서
  햄버거와 하단 4탭이 함께 존재한다. 6개 전체 메뉴 보존을 위한 의도는 task에 있으나, 두 내비 간 상태·접근성
  교차 검증은 별도 정본이 없다. 심각도 **정리 필요**.
- **표시만 변경:** `DisclosureHub.tsx:58`의 작은 caption 숨김, `WhyDisclosure.tsx:32`의 `<br>` 제어는
  동작/데이터 분기가 아니므로 제1원칙 위반으로 보지 않았다.
- 183 투약 설명은 동일 DiseaseCard 동작을 유지했고 별도 모바일 로직을 만들지 않았다. 270은 동작은 공유하고
  폰트 크기만 JS 선택하므로 "동작 동일하면 억지 분기 금지" 선례에 부합한다.

## D. 265 토큰·가드 준수

### D-0. 가드 범위

`src/components/mobile/mobileTokens.test.ts:22-33,51-63`은 `src/components/mobile/` 아래 `.ts/.tsx`만
읽고 `text-[Npx]`, `fontSize: N`, `font-size: Npx`만 검사한다. 다음은 검사하지 않는다.

- 모바일에서 실제 렌더되지만 폴더 밖인 `Disclosure.tsx`, `AnalysisProgress.tsx`, `InstallPrompt.tsx`,
  `Layout.tsx`, `DisclosureHub.tsx`.
- Tailwind 별칭 `text-xs`(12px), `text-sm`(14px), `text-caption`(12.5px).

### D-F1 — 실제 모바일 15px 하한 우회

| 위치 | 모바일 표시값 | 상태 |
| --- | --- | --- |
| `src/components/AnalysisProgress.tsx:47-49` | 분석 대기 안내 `11px` | **미승인 우회**. 268b 모바일 컴포넌트지만 폴더 밖이라 가드 누락 |
| `src/components/InstallPrompt.tsx:76-87` | 제목/버튼 14px, 본문 13px | **미승인 우회**. 264 PWA UI가 가드 밖 |
| `src/pages/Disclosure.tsx:1914-1945` | 모바일 시트 안 동의문 `text-xs`=12px | **미승인 우회**. consentSlot 재사용으로 모바일에 그대로 들어감 |
| `src/pages/Disclosure.tsx:2169-2204,2261-2301` | 모바일 업로드 화면의 badge/help/file list 12~14px | **미승인 우회**. 268a 시트 밖 기존 폼도 모바일에 표시 |
| `src/pages/Disclosure.tsx:2352-2364` | 구형 CTA 14px | **미승인 우회**이자 A-F1 |
| `src/components/Layout.tsx:275-319` | 모바일 햄버거 메뉴 12.5~14px | **미승인 우회**. 전역 레이아웃이 가드 밖 |
| `src/pages/DisclosureHub.tsx:51-79` | 모바일 탭/버튼 12~14px | **미승인 우회** |
| `src/components/ui/Badge.tsx:18-40` + `Disclosure.tsx:483,818` | Q 배지 12.5px | **의도적 예외**. 267/270 task에 범위 제외·Human 결정 대기로 기록됨 |

- 증상/위험: 테스트가 PASS해도 고객이 실제 보는 모바일 보조 문구가 15px 미만이다.
- 심각도: **실사용 결함**(정책/가드 허위 안전성). Q 배지는 의도적 예외라 별도 결정 항목.
- 수정 방향 제안(구현 금지): 경로 기반이 아니라 `useIsMobile` 분기 및 모바일 진입점의 실제 렌더 결과 computed
  style을 검사하고, named Tailwind size도 px로 해석한다. 예외는 allowlist+사유+Human 결정 번호로 제한한다.

### D-1. 임의 수치·키 정합

- `MOBILE_TYPO`, `MOBILE_TOUCH`, `MOBILE_LAYOUT`, `STATE_SURFACES`, swipe/toast 규칙은
  `src/components/mobile/tokens.ts:4-69`에 있다.
- 실제 모바일 컴포넌트에는 토큰 밖 수치가 다수 남는다. 예: overlay z 9990/9997/9998/9999,
  BottomSheet max-width 560px·max-height 60vh(`BottomSheet.tsx:68-100`), 보장표 폭 720px와 열 72/80px
  (`CoverageMobileView.tsx:173-175,277-278`), padding 8/12px(`MobileBottomNav.tsx:66`,
  `UpdatePrompt.tsx:23-27`), 업로드 진입 버튼 56 하드코딩(`Disclosure.tsx:2330-2337`).
- 모든 수치를 토큰화해야 한다는 명시 계약은 없으므로 각각을 결함으로 단정하지 않았다. 다만 overlay z와
  bottom spacing이 분산된 것은 A-F2의 직접 위험이며, **z-index/bottom surface 토큰 부재는 잠재 위험**이다.
- 270 폰트 맵은 정합하다. 공유 키 `DISEASE_CARD_TYPO_KEYS`와 `DiseaseCardTypoKey`를 정의하고 모바일/데스크톱
  모두 `Record<DiseaseCardTypoKey,string>`을 사용한다(`diseaseCardTypography.ts:17-67`,
  `Disclosure.tsx:420-441`). 키 누락/추가는 tsc가 잡는다.

## E. 문서 정합

### E-0. 기준선

- 감사 착수 시 세 문서는 frontend **342 passed / 35 files**, backend **838 passed, 8 skipped**로 일치했다.
- 감사 도중 별도 프로세스가 276a·276b를 `f254e8c`·`d95e56b`로 커밋하면서
  `AGENTS.md:103-104`, `CLAUDE.md:299-300`, `.agent-harness/verify.md:19-35`를 모두 frontend
  **342 passed / 35 files**, backend **861 passed, 8 skipped**로 함께 갱신했다. 완료 시점에도 세 문서와
  최신 handoff의 기준선은 일치한다. 275가 이 파일들을 수정한 것은 아니다.

### E-F1 — verify overview 설명이 259 이전 상태

- 위치: `.agent-harness/verify.md:80-81`
- 증상/위험: overview 정본을 "회사 열 미생성·합계 열만"이라고 적었으나 259는 26/26 귀속된 overview에서
  `[전]/[후]` 각 15개 회사 열을 렌더하도록 완결했다
  (`tasks/BOHUMFIT-259-overview-render-and-carry.md:1,47-62`). 스모크 스크립트도 회사 귀속과
  회사합=합계를 검사한다(`scripts/smoke-coverage.mjs:35-46,79-128`).
- 심각도: 정리 필요
- 재현 조건: verify 문서만 보고 라금실 정본 엑셀 기대값을 판정할 때 정상 15열을 오판.
- 수정 방향 제안(구현 금지): 259 정본인 15열·해지 0 전=후·회사합=합계를 반영한다.

### E-1. handoff 커밋 해시

263~273 구현/보정 커밋 short SHA를 handoff에서 검색한 결과 모두 최소 1회 존재했다:
`6e87cc5`, `901cd07`, `c24bfa7`, `9eef3cf`, `5751ef2`, `a6a2bd5`, `04bef53`,
`d6059b0`, `6333119`, `e8f358c`, `f40c9b3`, `d93bcb6`, `1884f57`, `2e55cf7`, `bce4cd5`.
**해시 누락은 확인되지 않았다.**

다만 task 파일 머리말은 완료 후 갱신되지 않아 264·266·267은 Codex 커밋 대기, 268b·269a·269b·270·271·
272·272b·273은 Claude Code 구현 단계로 남아 있다. git log/handoff와 충돌하는 **정리 필요** 상태다.

### E-2. 263~273 미완결·보류 이력

| 원 task | 항목 | 현재 상태·사유 |
| --- | --- | --- |
| 263 | PWA/모바일 구현 | 264~273으로 대부분 대체·해소. 원 감사의 디자인 시안 Next는 후속 구현 이력으로 사실상 종료 |
| 264 | 설치·오프라인 실기기 | **미완결** — Human 폰/비행기모드 확인 기록 없음 |
| 265 | SW 업데이트 안내 실동작 | **미완결** — waiting worker를 만드는 후속 SW 변경이 없어 실제 노출/클릭 검증 없음 |
| 265 | 5건/24h 오프라인 캐시 | **미완결/결함** — B-F4처럼 호출부 0 |
| 266 | 종합비교/Y/N 모바일 | 267에서 해소. 스와이프 감각 Human 실기기 확인은 미완결 |
| 267 | Q 배지 4단 통합 여부 | **결정 대기** — 현행 Q1~Q5 유지. DiseaseCard 폰트는 270에서 해소 |
| 268a | Railway proxy timeout·worker 대시보드 실측 | **부분 확인/미완결** — 레포 설정·공개 health 확인 이력은 있으나 대시보드 운영값 직접 확인 기록 없음 |
| 268b | 실시간 티커 | 구현 완료. 백그라운드 알림은 268c로 이관 후 미착수 |
| 269a | 모바일 저장 리포트/업셀 노출 | **Human 결정 대기** — 모바일 홈은 usage warning만, 업셀 카드 미배선 |
| 269b | iOS safe-area·키보드·백그라운드 | **Human 실기기 대기** |
| 270 | Q 배지 12.5px·모바일 글자 계층 체감 | **Human 결정/실기기 대기** |
| 271 | 오류 화면 익명화 | 화면은 해소. B-F1/B-F2/B-F5의 저장·로그·console은 이번 교차 감사에서 새로 발견 |
| 272 결함 B | 상품명 회사명 오염 | 272b에서 해소됨 |
| 272b | 회사명이 `새마을금고`로 짧게 잡힘 | **272c 잔여** — `_join_split_insurer_fragments` 착수점 기록됨 |
| 273 | PrimaryAction↔네비 | 구현 해소. 하단 점유 138~172px와 iOS 체감은 Human 대기; A-F1/A-F2는 별개 잔여 |

## F. 백로그 정합 재판정

| 항목 | 코드 기준 현재 유효성 | 근거 |
| --- | --- | --- |
| 262 D-3 로컬 빌드 근본 해결 | **유효·미착수** | `AGENTS.md`/`verify.md:44-61`에 Windows Application Control·343kB 껍데기·프로덕션 대체 검증이 계속 정본. WSL/CI 빌드 경로 없음 |
| 262 D-6 PDF 렌더 CI 골든 | **유효·미착수** | `.github/workflows/ci.yml`에 PDF 페이지/텍스트 골든 검사 없음. 261 로컬 실렌더만 존재 |
| 262 D-15 파싱 성능 | **유효·미착수** | `backend/pipeline/pdf_parser.py`의 pdfplumber 전체 파싱 구조 유지. 268b는 병렬 진행 표시이지 page 역할 분류/선택적 layout 추출이 아님 |
| 272c 회사명 짧게 잡힘 | **유효** | `_join_split_insurer_fragments`가 KNOWN 정확 일치 우선 후 접미 폴백(`backend/coverage/parser.py:148-210`). 272b task가 `새마을금고` vs `새마을금고중앙회` 잔여를 명시 |
| 268c 백그라운드·알림 | **유효·미착수** | 제품 코드에 Push/Notification 구현 0; 조사안만 `docs/mobile-analysis-progress-survey.md:80-85`에 존재 |
| 모바일 업셀 정책 | **유효·결정 대기** | desktop `showUpsell`은 `Dashboard.tsx:111-112,274-289`; 모바일 분기 `MobileHome` props에는 전달하지 않음(`:117-139`) |
| T2 80%이상 후유장해 표시 | **유효·Human 결정/스키마 선행** | 243은 기타 보존·후유장해 집계 제외를 확정(`constants.py:250,291`). 276b도 T2를 의도적으로 미구현했다. 제안서 [후]에 넣으려면 `coverage_meta`/스키마가 기타 라벨을 수용해야 함 |

요청된 백로그 중 이미 해소됐거나 무의미해진 항목은 **없다**. 다만 D-3은 기능 결함이 아니라 검증 인프라,
D-6은 수동 검증을 자동화하는 잔여다. 268b 티커 자체를 268c가 대체하는 것이 아니라, 268c는 탭 이탈 후
완료 알림이라는 별도 요구다.

## 2. 우선순위 정렬 후속 태스크 후보

1. **BOHUMFIT-277 후보 — PII 저장·로그 경계 봉인(고위험)**
   - B-F1 raw parse_errors 서버 익명화 + history 저장 전 deep scrub.
   - B-F2 analyzer 성공/실패 로그 원본 파일명 제거.
   - B-F3 sessionStorage user-bound + 전 로그아웃 경로 삭제.
   - B-F5 Sentry/console 최종 문자열 scrub 및 기존 DB 처리 Human 결정.
   - 완료 기준: 이름 포함 합성 filename으로 화면·응답·history payload·로그·Sentry event fixture 전 경로 0.
2. **BOHUMFIT-278 후보 — 모바일 bottom-surface 단일화(중위험)**
   - A-F1 구형 CTA 제거/268a 시트 단일화, A-F2 Install/Update/Toast/네비/액션 공통 overlay 계약.
   - 완료 기준: 상태 조합 매트릭스와 iOS safe 0/34px 히트 테스트.
3. **BOHUMFIT-279 후보 — 오프라인 캐시 A안 실제 동선·고지 정합(중~고위험, Human 정책 선행)**
   - A안 유지 시 IndexedDB 저장/조회/오프라인 진입 및 모든 저장소 통합 삭제. 철회 시 문구 제거.
   - 완료 기준: 계정 전환·24h 경계·5건 상한·비로그인·오프라인 실브라우저.
4. **BOHUMFIT-280 후보 — 모바일 가드 렌더 기반 확장(저~중위험)**
   - 폴더/정규식 blind spot 제거, named Tailwind size와 실제 모바일 DOM computed font 검사.
   - Q 배지 예외는 Human 결정 후 명시 allowlist.
5. **BOHUMFIT-281 후보 — 하네스 문서 정합 정리(문서 전용)**
   - verify overview 259 정본 반영, 264~273 task owner/완료 메타 정리, 완료/대기 보드 단일화.
6. 기존 백로그 유지: **272c** → **268c** → **D-3/D-6** → **D-15** → 모바일 업셀 → T2 80%이상
   (T2는 Human 정책·스키마 결정 선행).

## 3. 확인 불가 목록

- 실제 iOS safe-area 34px와 375/390/430px에서 A-F2 조합의 좌표/히트 테스트: 실기기·브라우저 미사용.
- InstallPrompt와 UpdatePrompt의 프로덕션 동시 노출: 설치 이벤트/waiting worker 없음.
- 프로덕션 Railway 로그·Sentry에 과거/현재 PII가 실제 전송·보존됐는지: 운영 콘솔 미접속.
- 기존 Supabase history 행에 이름 포함 parse_errors가 존재하는지와 건수: 프로덕션 DB 미접속.
- 사용자 기기의 IndexedDB/sessionStorage 실재 데이터: 사용자 브라우저 미접속.
- 실 PDF 기반 화면/PDF/엑셀/카카오 결과 재현: PII를 열지 않는 조사 방식으로 수행해 미실행.

위 항목은 코드 근거가 없는 결론으로 채우지 않았다.

## 4. 검증 체크리스트

- [x] 루트 게이트·AGENTS.md·CLAUDE.md·locks·handoff 확인
- [x] `fixed`/`sticky` 하단 요소와 동시 조합 전수 정적 열거
- [x] PII 표시·복사·저장·로그·콘솔·메모리 경로 추적
- [x] `useIsMobile` 7파일·10호출 및 CSS 숨김 분기 추적
- [x] 265 하한 가드의 스캔 범위·blind spot 확인
- [x] 265 IndexedDB 삭제 5경로를 단일 auth 사용자-id 전이 지점까지 추적; sessionStorage 제외 확인
- [x] 세 기준선 문서 수치 일치 확인; verify overview 설명 불일치 별도 기록
- [x] 263~273 handoff 구현 해시 누락 0 확인
- [x] 262 D-3/D-6/D-15·272c·268c·업셀·T2 현재 유효성 재판정
- [x] 275 제품 코드 변경 0; 선행 276a·276b 변경 무접촉
- [x] 실 PDF·PII·엑셀·임시 산출물 생성/저장 0
- [x] 확인 불가 항목과 이유 명시

## 5. Next

1. **Human/Chat** — B-F1~B-F5를 묶을 PII 경계 봉인 태스크를 최우선 발번하고, 기존 DB raw
   parse_errors 점검/정리 권한과 오프라인 캐시 A안 유지 여부 결정.
2. **Chat** — 구형 CTA 포함 bottom-surface 단일화 태스크 발번.
3. **Human** — iOS 실기기에서 설치·업데이트·토스트·네비·액션 조합 검수.
4. **Chat** — 문서 정합(verify overview·task owner) 저위험 정리 후 기존 272c/268c 백로그 진행.
