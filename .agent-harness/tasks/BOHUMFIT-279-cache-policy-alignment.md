# BOHUMFIT-279 — 오프라인 캐시 A안 철회 · 고지 문구 정합

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중위험 — ★**법적 고지 문구**. 기능 추가 0. git 쓰기 금지(커밋 Codex).
Date: 2026-08-08 · 기준 HEAD `8cce8ae`(277) · 선행 BOHUMFIT-275 B-F4
★3건 순차 세션의 **2번**(278 → 279 → 276c). 278 변경분은 되돌리지 않았다.

## ★Human 확정 (재검토 금지)
265 오프라인 캐시 A안을 **철회**한다. IndexedDB를 배선하지 않고 **고지를 실동작에 맞춘다**.

---

## Step 1 — 실측 (코드 무변경)

### 방침·동의문의 저장 관련 문구 (수정 전)
| 위치 | 문구 |
|---|---|
| `PrivacyPolicy.tsx:50` | 히스토리 저장 요청 시 **90일** |
| `PrivacyPolicy.tsx:51` | 요약 자동 기록 **최근 10건·7일** |
| ★`PrivacyPolicy.tsx:53` | **"최근 분석 5건이 … 24시간 임시 보관"**(265 A안) |
| ★`ConsentGate.tsx:45~46` | **"오프라인 열람을 위해 최근 5건이 이 기기에 24시간 임시 보관"** |
| `TermsOfService.tsx:43` | "연중무휴 24시간" — 저장과 무관(오탐) |

### ★실제 저장물 전수 (대조표)
| 저장소 | 실제 | 문구 상태(수정 전) |
|---|---|---|
| 서버 `saved` | 90일(`HISTORY_RETENTION_DAYS = 90`) | ✔ 일치 |
| 서버 `recent` | 10건·7일(`HISTORY_RECENT_RETENTION_DAYS = 7`) | ✔ 일치 |
| ★**IndexedDB** | ★**저장 안 함** — `saveAnalysis`·`listAnalyses`·`getAnalysis` 제품 호출 **0건** | ★**있다고 단정**(거짓) |
| ★**sessionStorage** | ★**10분**(277 기준: user-bound·로그아웃/계정 전환 즉시 삭제·탭 닫으면 소멸) | ★**문구에 없음**(누락) |
| localStorage | 설치 안내 닫힘 시각·투어 — 건강정보 0 | 해당 없음 |
| 업로드 원본 | 분석 후 미저장 | ✔ 일치 |
→ **양방향으로 어긋나 있었다**(없는 것을 있다고 하고, 있는 것을 빠뜨렸다).

### `analysisCache.ts` 사용처 재확인
제품 코드 호출 **0건**(테스트 파일만). ★단 `clearAnalysisCache()`는 `AuthContext`에서 **호출 중**이며
277의 `clearSessionResult()`와 같은 지점에 있다.

---

## Step 2~4 — 구현

### Step 2 — 문구 정합
- `PrivacyPolicy.tsx` 4항: A안 조항을 **"다시 보기용 기기 내 임시 보관: … 브라우저 세션 저장소에 10분 …
  로그아웃·다른 계정 로그인 시 즉시 삭제 … 서비스 서버로 별도 전송되지 않습니다"** 로 교체.
- `ConsentGate.tsx`: 같은 사실로 정합("이 기기에 **10분간 임시 보관**(로그아웃·계정 전환 시 즉시 삭제)").
- ★서버 90일·7일 조항과 업로드 원본 미저장 문구는 **그대로** 뒀다(사실이므로).
- ★법적 고지라 **실제보다 넓게도 좁게도** 쓰지 않았다 — 수치는 구현 상수(`SESSION_RESULT_TTL_MS`)와
  테스트로 묶었다.

### Step 3 — 미사용 코드 처리
`analysisCache.ts`를 **삭제하지 않고 미사용·재개 조건을 파일 상단에 명시**했다.
- 삭제하면 재개 시 265 설계(스토어 분리·5건·24h·user-bound)를 처음부터 다시 해야 한다.
- ★`clearAnalysisCache()` 호출은 **유지** — 과거 잔여 레코드를 지우는 역할이고,
  277의 `clearSessionResult()`와 함께 단일 삭제 지점에 남는다(테스트로 고정).

### Step 4 — 결정 기록
`.agent-harness/decisions.md` 최상단에 A안 철회·사유·영향·**재개 조건 4가지**를 기록했다.

---

## 검증 결과 (1차 · 2026-08-08 · Windows 로컬)

- [x] ★사용자 노출 문구에 **"최근 5건"·"24시간 임시 보관"·"오프라인 열람" 0건**(주석 제거 후 검사)
- [x] ★기재 수치가 **실제 구현 상수와 일치**: `SESSION_RESULT_TTL_MS`=10분 · 서버 90/7일 상수 대조
- [x] 방침 ↔ 동의문 상호 일치(둘 다 90일·7일·기기 10분)
- [x] ★277 `sessionStorage` 삭제 계약 **무변경** · `clearAnalysisCache`·`clearSessionResult` 둘 다 유지
- [x] ★278 변경분 무회귀(같은 세션 1번 태스크 — 되돌리지 않음)
- [x] `npm test` **393 passed / 40 files** · backend **불변** · smoke PASS · tsc · lint
- [x] `backend/` diff 0 · `vite.config.*` diff 0 · **기능 추가 0**(문구·주석·결정 기록뿐)

### ★기존 테스트 4건 기대값 갱신 — 사유
`analysisCache.test.ts`(3건)·`updatePromptWiring.test.tsx`(1건)이 **A안 문구를 정답으로 고정**하고 있었다.
A안이 철회됐으므로 기대값을 **실동작(10분·계정 전환 삭제)** 으로 갱신했다.
★고지가 참조하는 구현 상수도 `analysisCache`(미배선) → **`sessionResultQueue`(실동작)** 로 바꿨다.
`MAX_ENTRIES`·`TTL_MS`는 재개 대비로 파일에 남지만 **더 이상 고지의 근거가 아니다**.

## Stage 목록 (Codex용)
★**279 단독 커밋**(278·276c와 분리). `PrivacyPolicy.tsx`·`ConsentGate.tsx`·`analysisCache.ts`(주석)·
갱신된 테스트 4건 + `cachePolicyAlignment279.test.ts`,
`tasks/BOHUMFIT-279-cache-policy-alignment.md`·`decisions.md`·`handoff.md`·`locks.md`

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-279): 오프라인 캐시 A안 철회 — 개인정보 고지 문구를 실동작에 정합
