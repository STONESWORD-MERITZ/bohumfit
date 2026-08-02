# 분석 진행 신호 실태 조사 (BOHUMFIT-268a)

작성: Claude Code · 2026-08-01 · 기준 HEAD `5751ef2`(267)
목적: **268b(분석 진행 구간) 설계 근거**. 이 문서는 조사 전용이며 백엔드 코드는 한 줄도 바꾸지 않았다.
원칙: **사실만 기록**. 확인하지 못한 것은 "확인 불가"로 적는다.

---

## 1. 분석 요청은 단일 POST 동기 응답인가

**그렇다. 작업ID·폴링 구조는 없다.**

| 엔드포인트 | 위치 | 형태 |
|---|---|---|
| `POST /api/analyze` | `backend/main.py:2085` | 멀티파트 업로드 → 분석 완료까지 **한 응답**으로 반환 |
| `POST /coverage/analyze` | `backend/main.py:1897` | 동일 |
| `POST /coverage/parse`·`/coverage/proposals/parse` | `1860`·`1938` | 동일 |

- 작업 큐·작업ID 발급·상태 조회(`GET /jobs/{id}` 류) 엔드포인트는 **레포에 존재하지 않는다**(전수 grep).
- 클라이언트도 단일 `fetch`로 받고 타임아웃만 길게 잡아 둔다
  (`Disclosure.tsx`: `AbortSignal.timeout(350_000)` — 서버 `ANALYZE_TIMEOUT_SECONDS=300`보다 50초 여유).
- 즉 **현재 사용자는 "업로드 후 최대 5분간 아무 신호 없이 기다린다"**. 268b가 풀려는 문제가 이것이다.

## 2. 응답 전에 존재하는 중간 산출물이 있는가

**있다 — 다만 지금은 로그로만 나가고 밖으로 흘릴 통로가 없다.**

`backend/analyzer.py`의 `run_analysis`(912행) 안에서 파일 단위로 파싱이 끝날 때마다 값이 확정된다:
- 순차 경로(270~282행): 파일 하나가 끝날 때마다 `all_records` 누적 · `parse_errors` 누적 ·
  `customer_name` 확정 · `_log_parsed(fn, pr)` 호출.
- 병렬 경로(285~300행, `BOHUMFIT-055`): `ProcessPoolExecutor` + `as_completed`로 **완료되는 대로** 결과가 들어온다
  (순서는 인덱스로 보존).

→ **"파일 3개 중 2번째 파싱 완료", "레코드 N건 수집"** 같은 신호를 만들 재료는 이미 존재한다.
현재는 `logger.info`로만 나가고 HTTP 응답 스트림·이벤트 버스가 없어 **클라이언트가 알 방법이 없다**.

## 3. SSE·폴링 도입 시 접촉 파일과 범위

| 방식 | 접촉해야 하는 곳 | `backend/pipeline/`·`coverage/` 무접촉 가능? |
|---|---|---|
| **SSE**(`StreamingResponse` + `text/event-stream`) | `backend/main.py`에 스트리밍 엔드포인트 신설 + `analyzer.run_analysis`에 **진행 콜백 인자** 추가 | **부분 가능**. `pipeline/`은 안 건드려도 되지만 `analyzer.py`는 콜백을 받도록 시그니처가 바뀐다. `analyzer.py`는 `pipeline/`이 아니라 오케스트레이터라 268a 금지 목록(`pipeline/`·`coverage/`·`main.py`)과는 별개 판단이 필요하다 |
| **폴링**(작업ID + 상태 조회) | `main.py`에 작업 저장소(메모리 dict 또는 외부 스토어) + 엔드포인트 2개 신설 + `analyzer` 콜백 | 동일. 추가로 **워커가 여러 개면 메모리 dict는 깨진다**(아래 4번) |

- 어느 쪽이든 **`pipeline/` 하위 모듈은 손대지 않아도 된다** — 진행 신호는 `analyzer.py`의 파일 루프에서 나온다.
- 프런트는 `Disclosure.tsx`·`CoverageRemodel.tsx`의 전송 호출부만 바뀐다(268a가 만든
  `uploadWithProgress`와 **분리된 계층** — 업로드 진행과 분석 진행을 섞지 않는다).

## 4. Railway 환경의 SSE·장시간 커넥션 제약

**설정 파일 근거로는 "제약 없음"을 확인할 수 없고, "제약 있음"도 확인할 수 없다 — 확인 불가.**

확인한 사실만:
- `railway.json`: `builder: DOCKERFILE`, `deploy.startCommand: null` — 타임아웃·프록시 설정 항목 **없음**.
- `Dockerfile`: `CMD ["bash", "/app/start.sh"]`. **`start.sh`는 레포에 없다**(빌드 시 생성되거나 이미지에 포함된 것으로
  보이나 확인 불가) → **워커 수·타임아웃 설정을 레포에서 읽을 수 없다.**
- 서버 자체 타임아웃은 `ANALYZE_TIMEOUT_SECONDS=300`(코드 상수)으로 확인된다.

→ ★**268b 착수 전에 Railway 대시보드에서 ①프록시 유휴 타임아웃 ②워커(프로세스) 수를 실측해야 한다.**
  워커가 2개 이상이면 **메모리 기반 작업 저장소(폴링)는 요청이 다른 워커로 가면 깨진다** — SSE는 커넥션이
  한 워커에 붙어 있어 이 문제가 없다.

## 5. Web Share Target 도입 시 필요한 변경과 플랫폼 제약

- 현행 `public/site.webmanifest`에 **`share_target` 없음**(264에서 넣지 않았다).
- 도입 시 필요한 변경:
  1. manifest에 `share_target`(`action`·`method: POST`·`enctype: multipart/form-data`·`params.files[]`) 추가
  2. `public/sw.js`에 **해당 action 경로의 POST를 가로채는 `fetch` 핸들러** 추가 —
     현행 SW는 `isCacheableRequest()`에서 **GET이 아니면 즉시 손대지 않고 통과**시키므로(264 계약),
     share target POST를 받으려면 **그 앞단에 별도 분기**가 필요하다. ★264의 PII 캐시 금지 계약은 유지해야 한다
     (공유받은 파일을 캐시에 넣으면 안 된다).
  3. 공유 진입 시 열릴 화면(파일이 이미 담긴 상태의 업로드 화면) 라우트
- 플랫폼 제약(일반적으로 알려진 사실):
  - **Android + 설치된 PWA에서만** 동작한다(Chrome 계열).
  - **iOS/Safari는 Web Share Target을 지원하지 않는다** — iOS 사용자는 기존 "파일 저장 후 선택" 동선이 유일하다.
  - → 268a가 시트에 넣은 **"카카오톡에서 받은 파일 → 저장 후 선택"** 안내는 iOS에서도 유효한 유일한 경로다.

## 6. 백그라운드 전환 + 완료 알림 경로

- 현행 `public/sw.js`의 리스너는 **`install`·`activate`·`message`·`fetch` 4개뿐**이다 —
  `push`·`notificationclick` 핸들러가 **없다**.
- 즉 지금 상태로는 **웹 푸시 알림을 받을 수 없다**. 필요한 것:
  1. `Notification.requestPermission()` 흐름(사용자 제스처 필요)
  2. SW에 `push`·`notificationclick` 핸들러 추가
  3. **서버 푸시를 쓰려면** VAPID 키 + 구독 저장소 + 발송 로직(백엔드 신설) — 범위가 크다
- **더 가벼운 대안**: 탭이 살아 있는 동안 분석 완료 시 `registration.showNotification()`을 호출하는 방식.
  서버 푸시 없이 SW 등록만으로 가능하고, 사용자가 다른 앱을 보고 있어도 알림이 뜬다.
  단 **브라우저가 탭을 종료(메모리 회수)하면 알림도 없다** — iOS Safari에서 특히 흔하다.

## 7. 268b 권장안 2개 (★최종 채택은 Human 결정 — 여기서는 확정하지 않는다)

### A안 — SSE 진행 스트림
- **구성**: `POST /api/analyze/stream`(신설) → `text/event-stream`으로 파일별 파싱 완료·단계 전환을 흘리고,
  마지막 이벤트로 최종 결과를 보낸다. `analyzer.run_analysis`에 진행 콜백 인자를 추가한다(선택 인자 — 기존 호출부 무영향).
- **장점**: 워커 수와 무관하게 안전(커넥션이 한 워커에 고정) · 폴링 대비 지연·요청 수가 적다 ·
  2번에서 확인한 **실제 중간 산출물**을 그대로 흘릴 수 있어 가짜 진행률을 만들지 않아도 된다.
- **트레이드오프**: Railway 프록시 유휴 타임아웃이 분석 시간(최대 5분)보다 짧으면 끊긴다(**4번 실측 선행 필수**) ·
  기존 `POST /api/analyze`를 남겨 둘지(이중 유지) 교체할지 결정이 필요하다 ·
  SSE는 요청 헤더를 실을 수 없어 `EventSource` 대신 `fetch` + `ReadableStream`으로 인증을 붙여야 한다.

### B안 — 작업ID + 폴링
- **구성**: `POST /api/analyze` 즉시 `job_id` 반환 → `GET /api/analyze/{job_id}`를 2~3초 간격으로 조회.
- **장점**: 표준적이고 프록시 타임아웃에 영향받지 않는다 · 앱이 백그라운드에 갔다 와도 이어서 조회할 수 있다 ·
  네트워크가 끊겼다 붙어도 복구가 쉽다.
- **트레이드오프**: **워커가 2개 이상이면 메모리 저장소가 깨진다**(4번) — Redis 같은 외부 스토어가 필요해질 수 있고
  그러면 인프라가 추가된다 · 폴링 요청이 늘어 rate limit(`5/minute` 등 현행 제한)과 충돌할 수 있어
  **분석 엔드포인트와 별도 한도 설계가 필요**하다 · 완료까지 지연이 폴링 간격만큼 생긴다.

### 공통 선행 조건
1. **Railway 프록시 유휴 타임아웃·워커 수 실측**(4번) — 이 값이 A/B 선택을 좌우한다.
2. 진행 신호는 **2번에서 확인된 실제 중간 산출물만** 쓴다. 재료가 없는 구간에서 가짜 퍼센트를 만들지 않는다
   (268a가 업로드 진행률에 적용한 것과 같은 원칙).
3. 업로드 진행(268a)과 분석 진행(268b)은 **다른 계층**이다 — 접합점은
   `src/components/mobile/MobileUploadSheet.tsx` 하단의 "268b 접합점" 주석 참조.
