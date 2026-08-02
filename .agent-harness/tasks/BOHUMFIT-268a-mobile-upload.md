# BOHUMFIT-268a — 모바일 업로드 UX + 분석 진행 신호 실태 조사

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Human(실기기·Railway 확인) / Chat(268b 발번)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex).
Date: 2026-08-01 · 기준 HEAD `5751ef2`(267)

## ★제1원칙
데스크톱 회귀 0. CSS 숨김 금지 — `useIsMobile`(matchMedia ≤767px) JS 분기만, matchMedia 부재 시 데스크톱 폴백.
266·267 선례 그대로.

## Step 1 — 현행 실측 (코드 무변경)

### 업로드 UI는 **공용이 아니라 화면별 중복 구현**이다
`type="file"` 전수 5곳:

| # | 위치 | 용도 | accept | multiple | 동의 게이트 | 트리거 |
|---|---|---|---|---|---|---|
| 1 | `Disclosure.tsx:2064` | **고지 PDF**(주) | `.pdf` | O | 자체 인라인 체크박스 2종 | 선택 후 **"AI 고지 리스크 점검" 버튼** |
| 2 | `CoverageRemodel.tsx:651` | **보장분석 PDF**(주) | `application/pdf` | ✗(1개) | `ConsentGate`(`agreed`) | **선택 즉시 업로드+분석** |
| 3 | `CoverageRemodel.tsx:924` | 신규 가입제안서(부) | — | O | — | 선택 즉시 파싱 |
| 4 | `Disclosure.tsx:1080` | 비급여 영수증(계산기 섹션) | `image/*,application/pdf` | ✗ | — | 파일명 표시만 |
| 5 | `InsuranceCalculator.tsx:278` | 별도 화면 | `application/pdf` | O | `ConsentGate` | — |

- **동의 체크가 두 갈래다**: 고지는 `consent`(민감정보) + `subjectConsent`(agent 모드 제3자 동의) **인라인 체크박스**,
  보장분석은 **`ConsentGate` 컴포넌트**(`agreed`). ★공용 컴포넌트가 아니므로 268a는 **각 화면의 기존 게이트 조건식을
  그대로 재사용**한다(조건 신설 0·문구 변경 0).
- **제한값**(`Disclosure.tsx:27~29`): 최대 **10개** · 개별 **15MB** · 총 **40MB**. 백엔드도 같은 상수로 413을 낸다.
- 고지 업로드는 **드래그앤드롭 + 숨김 input(`fileRef`)** 구조이고, `analyze()`가 `fileRef.current.files`를 읽는다.
  ★모바일 시트는 **같은 `fileRef`에 파일을 주입**해야 기존 분석 경로가 그대로 동작한다.

### 이미지(카메라 촬영) 수용 여부 — **수용하지 않는다**
- `/coverage/analyze`(`backend/main.py:1910`)는 `fname.lower().endswith(".pdf")`가 아니면 **400**.
- `/api/analyze`(고지)는 확장자 검사가 없지만 파서가 `pdfplumber` 기반이라 이미지는 파싱에 실패한다.
- → **"카메라로 촬영" 항목은 비활성 + "준비 중"** 으로 두고 사유를 조사 문서에 남긴다(백엔드 임의 변경 금지).

### 267까지의 모바일 분기 패턴
`useIsMobile` 사용처 = `CoverageInsightBlocks.tsx`·`CoverageRemodel.tsx`·`Disclosure.tsx`.
입도는 **렌더 블록 단위 조건부 렌더**(`{isMobile && ...}` / `{!isMobile && ...}` 또는 early return).
268a도 동일 입도로 붙인다.

## Step 2~4 — 구현
- `src/components/mobile/MobileUploadSheet.tsx` 신설(265 `BottomSheet`·`PrimaryAction` 재사용).
  항목 3종: **파일에서 선택**(기존 input 위임) / **카메라로 촬영**(★비활성·"준비 중") /
  **카카오톡에서 받은 파일**(별도 API 없이 같은 피커 + "카카오톡 → 파일 저장 후 선택" 안내).
- 동의는 각 화면의 **기존 상태·조건식**을 props로 받아 그대로 쓴다(문구 diff 0).
- 업로드 진행률: `src/lib/uploadWithProgress.ts` — **XHR `upload.onprogress` 실측 바이트**만 사용.
  ★진행률을 못 잡는 경로에서는 **가짜 퍼센트를 만들지 않고** 파일명·개수·용량만 표시한다.
  요청 헤더·엔드포인트·에러 처리는 현행 fetch 경로와 **동일한 계약**을 유지한다.
- 업로드 완료 → 분석 대기 진입 지점에 **268b 접합 마커 주석**을 남긴다.

## Step 5 — 조사 문서
`docs/mobile-analysis-progress-survey.md` (사실만·확인 불가는 명시).

## 검증 결과 (1차 · 2026-08-01 · Windows 로컬 · 전 게이트 실제 실행)

- [x] `npx tsc -p tsconfig.app.json --noEmit` **PASS** · `tsconfig.node.json` **PASS**
- [x] `npm run lint` **PASS**(경고 0)
- [x] `npm test` **217 passed / 27 files**(기준선 203 + 신규 **14**) · 회귀 0
- [x] `cd backend && python -m pytest -q` **792 passed, 8 skipped**(불변) · ★**`backend/` diff 0**
- [x] `npm run smoke:coverage` **PASS**(정본 2건 기준값·불변식 일치)
- [x] `npm run build:verify` **343,225 B 예상 FAIL**(248 로컬 껍데기 — 264~267과 동일 수치)
- [x] ★**데스크톱 4화면 HEAD 대비 실렌더 동일**(266·267 방식): `Disclosure` **업로드 단계**(파일 선택·동의 후) ·
      `Disclosure` **분석 결과 화면** · `CoverageRemodel` 결과 화면 · `StageComparisonTable`/`YnFlagTable` —
      전부 `innerHTML`·노드 수 **완전 일치**. 빈 화면 오통과 방지로 실제 마커(`민감정보(건강에 관한 정보)`·
      `t.pdf`·`복사하기`·`⑤` 섹션·`min-w-[560px]`·`min-w-[420px]`)와 노드 수 하한을 함께 단언했다.
      사본·일회성 스크립트는 검증 후 **삭제**(레포 잔재 0).
- [x] 터치 44px·주 액션 56px 준수(테스트로 고정) · 시트 내 폰트 15px 이상
- [x] matchMedia 미지원 → 데스크톱 폴백(`useIsMobile` 구현·265부터 동일)
- [x] `vite.config.*` diff **0** · **ConsentGate diff 0**(고지 화면은 애초에 ConsentGate를 쓰지 않고
      자체 인라인 동의를 쓰며, 그 문구·조건식도 **변경 0**)
- [x] **375/390/430px 가로 넘침 0** — Codex가 실제 Chromium 뷰포트에서 세 폭 모두
      `scrollWidth == clientWidth`를 확인했다. 파일 선택·카카오 안내·카메라 비활성 사유·44/56px도 함께 실측했다.

### 구현 요약
- `MobileUploadSheet` — 파일 선택 3종(파일에서 선택 / **카메라 촬영 = 비활성·"준비 중"** / 카카오톡 안내) +
  선택 결과(파일명·개수·총 용량) + **호출부 동의 슬롯** + 진행 표시. ★새 input을 만들지 않고 **호출부의 기존
  `fileRef`를 눌러** 기존 분석 경로(`fileRef.current.files`)를 그대로 살렸다.
- `uploadWithProgress` — XHR `upload.onprogress` **실측 바이트**만. `lengthComputable`이 아니면 **퍼센트를 만들지
  않고** `null`을 흘려 화면이 전송량만 보여준다. 헤더·엔드포인트·402 처리·`detail` 오류 규약은 기존 fetch와 동일.
- `Disclosure.tsx` — 모바일에서만 XHR 경로를 타고(데스크톱은 기존 fetch 그대로), 동의 블록은 **변수로 추출해
  위치만 바꿔** 재사용(문구·마크업·조건식 diff 0). 진입 버튼은 56px.

### 자체 정정 2건
1. 처음에 동의 블록 교체를 잘못 편집해 JSX 구조를 깨뜨렸다 → 즉시 되돌리고, 블록을 `consentBlock` 변수로
   추출하는 방식으로 다시 작성했다(Fragment는 DOM 노드를 만들지 않아 데스크톱 렌더가 동일하다).
2. 시트에 개별 파일 크기를 넘기려고 렌더 중 `fileRef`를 읽었더니 `react-hooks/refs` lint가 잡았다(정당한 지적).
   → 기존 상태(`selectedNames`·`selectedSize`)만 쓰도록 인터페이스를 `{ names, totalBytes }`로 바꿨다.

### ★남긴 접합점
`MobileUploadSheet.tsx` 하단에 **268b 접합점 주석** — "업로드 전송 완료"와 "분석 대기"의 경계를 명시했다.

### 보장분석(CoverageRemodel) 업로드는 이번에 손대지 않았다
Step 1 실측대로 **선택 즉시 업로드+분석**이라 시트로 감쌀 중간 단계가 없고, 파일도 1개뿐이라
"파일 선택 3종" 시트의 이득이 고지 화면만큼 크지 않다. 데스크톱 회귀 위험만 늘어나므로
**268b 이후 별도 판단**으로 남긴다(기록만).

## ※패킷의 "샌드박스 실행 불가" 문구에 대하여
패킷 말미의 "샌드박스에서 tsc/build/pytest 실행 불가 · 마운트에서 git 실행 금지"는 **퇴역한 Cowork 환경**
전제다(`CLAUDE.md` [퇴역] 절). 현행 Claude Code는 Windows 로컬에서 직접 실행하므로 **전 게이트를 실제로 돌렸고**
결과를 아래에 기록한다. git은 읽기만 사용했다(쓰기 0).

## Codex 2차 검증 (2026-08-02 · Windows 권위)

- 전체 게이트 재현: app/node tsc·lint·`npm test` **217 passed / 27 files**·backend
  **792 passed, 8 skipped**·`smoke:coverage` 정본 2건 PASS. `npm run build`는 **343,225 B**를 만들었고
  `build:verify`가 248 계약대로 exit 1로 거부해 **예상 FAIL**로 판정했다.
- 실제 Chromium 375/390/430px: 세 폭 모두 가로 넘침 **0**, 시트 폭=뷰포트, 소스 행 최소 74px,
  핸들 `::before` 히트영역 **44px**, 주 액션 **56px**. 카메라는 disabled+"준비 중"+PDF 전용 사유를 보였고,
  카카오 항목은 기존 multiple 파일 피커를 열어 합성 PDF 선택 후 파일명·실제 용량을 표시했다. 콘솔 경고·오류 0.
- 첫 실측에서 열린 시트 뒤 문서가 **520px 스크롤되는 결함**을 발견했다. 같은 범위 최소 보정으로
  `BottomSheet`가 body/root를 고정하고 닫을 때 원래 스크롤·스타일을 복원하도록 했으며, 보정 후 같은 조작에서
  `scrollY` **0→0**을 재현했다. React 검토에 따라 스크롤 락 효과와 Esc 리스너 효과를 분리해 진행 이벤트 렌더 때
  락이 불필요하게 재설정되지 않게 했다.
- 모바일 XHR 실동작 계약: 정상/402/422/503/네트워크 오류/타임아웃을 실제 `Disclosure` 호출부에서 재현했다.
  엔드포인트·Bearer 헤더는 데스크톱 fetch와 같고, `detail` 문구·402 전환도 동일했다. XHR에도 데스크톱과 같은
  **350초** 타임아웃을 추가해 무한 대기를 막았고, `lengthComputable=false`는 퍼센트 없이 실제 전송량만 표시했다.
  시트가 분석 중 닫혀 진행 표시가 사라지던 결함은 `open={uploadSheetOpen || loading}`으로 보정했다.
- HEAD 별도 사본 동등성: 동의 문구 2종 문자열·동의 0/1/2 상태 활성화 `[비활성, 비활성, 활성]` 일치.
  데스크톱 4화면의 `innerHTML` SHA-256/노드 수는 업로드
  `b195a518…`/51, 결과 `ae3ee525…`/99, Coverage `e07920c9…`/442, 종합비교+Y/N
  `055e6e1a…`/82로 HEAD와 완전 일치했고 빈 화면 방지 마커도 통과했다. matchMedia 부재는 데스크톱 폴백.
- 보호 영역: backend·coverage core·pipeline·vite config·CoverageRemodel 업로드·265 캐시·supabase diff 0.
  10개/15MB/40MB 제한과 Q1~Q5 판정·기간 라벨 불변, PII·실 PDF·임시 하네스·렌더 산출물 0.

## Stage 목록 (Codex용)
프런트 소스·신규 컴포넌트·테스트, `docs/mobile-analysis-progress-survey.md`,
`tasks/BOHUMFIT-268a-mobile-upload.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-268a): 모바일 업로드 하단 시트·동의·업로드 진행 실측 + 분석 진행 신호 실태 조사
