# Decisions

Record durable project decisions here. Keep entries short and dated.

### 2026-05-30 Codex-Only Harness

Decision:
BOHUMFIT work will proceed with Codex as the single working agent by default.

Reason:
The previous Claude/Cowork -> Codex verification sequence created unnecessary handoff overhead.

Impact:
Codex owns implementation, verification, handoff notes, scoped staging, commit, and push when the user requests publication. Historical Claude/Cowork entries remain archival context only.

### 2026-05-30 Deterministic Disclosure Results

Decision:
For identical input PDFs and the same reference settings, disclosure-deterministic fields must be stable across repeated runs.

Reason:
The user observed that running the same materials repeatedly can change disclosure results, which breaks trust in the rule engine.

Impact:
Disease code, disease name, counts, question classification, and deterministic evidence must not change run-to-run. AI-assisted extra-exam/recheck opinion text may vary, but it must not mutate deterministic disclosure counts or disease identity.

### 2026-06-15 Brand Assets: Source Master vs Deployed

Decision:
`brand/` (repo root) = 정본(소스 마스터)이다. 배포본(앱이 실제 참조하는 파일)은 `public/`에 둔다. 앱의 favicon/아이콘/og 참조는 항상 `public/`(루트 `/…` 경로)을 가리키며, `brand/`를 직접 참조하지 않는다.

Reason:
정본(편집용 원본·다양한 포맷/사이즈)과 배포본(런타임 정적 제공)을 분리해, 디자인 변경은 `brand/`에서 하고 `public/`로 내보내 배포 일관성을 유지하기 위함.

Impact:
- `index.html`/메타 참조는 `public/favicon.svg`·`public/og-image.svg` 등 `public/` 자산만 가리킨다(확인됨).
- 새 아이콘/파비콘은 `brand/`에서 마스터를 갱신 후 `public/`로 내보내 참조한다.
- `brand/`의 미배포 자산(favicon.ico, favicon-16/32.png, apple-touch-icon-180.png 등)을 쓰려면 `public/`로 복사하고 `index.html`에 링크를 추가하는 별도 작업이 필요하다.

### 2026-06-15 Non-Surgery Exclusion Source

Decision:
비수술 오분류 제외 코드명은 `backend/pipeline/surgery_exclusions.py`의 `NON_SURGERY_NAMES` 한 곳에서만 추가·관리한다. 신규 제외 추가 시 회귀 테스트를 동반한다.

Reason:
수술 감지 알고리즘과 예외 코드명을 분리해 오분류 보정을 안전하게 확장하기 위함.

Impact:
새 비수술 제외명은 helpers나 aggregator에 흩어 넣지 않고 중앙 목록과 `test_surgery_exclusions.py`에 함께 추가한다.

### 2026-06-16 General Department Rows Are Pharmacy-Like

Decision:
진단과=`일반의` basic/unknown 행은 모두 약국성 기본진료로 보아 통원 집계에서 제외한다. 상병코드 유효성이나 `$` 여부로 예외를 두지 않는다. (BOHUMFIT-040)

Reason:
일반의 기본진료 행은 실제 통원 병력으로 해석하면 과집계 위험이 크고, 처방조제·입원 경로와 분리해 다루는 편이 안전하다.

Impact:
`_keep_basic_general_row`는 항상 `False`이며, 비일반의 유효코드·처방조제 투약·NHIS/병원 입원 경로는 이 결정의 영향을 받지 않는다.

### 2026-06-16 AI Is Q2-Only

Decision:
AI(Gemini)는 Q2 추가검사·재검사 보조 판단에만 관여한다. Q1, Q3, Q4, Q5는 결정론 룰 전용이다. (BOHUMFIT-038)

Reason:
AI가 진단·입원·수술·통원·투약·중대질병 질문을 직접 분류하면 고지 결과가 비결정적으로 흔들릴 수 있다.

Impact:
`result_builder._build_pool`의 AI Q2 한정 가드는 유지해야 하며, AI 출력은 결정론 고지 건수·코드·질문 분류를 변경하지 못한다.

### 2026-06-16 Q5 Major Disease Is Code-Only

Decision:
Q5 중대질병은 결정론 `health_q5_codes` 코드매칭만으로 판정한다. AI는 Q5 중대질병 판정에 관여하지 않는다. (BOHUMFIT-038, BOHUMFIT-039)

Reason:
중대질병은 코드 목록과 약관성 분류가 핵심이므로 AI 추정으로 과분류하면 위험하다.

Impact:
Q5 코드풀 변경은 `backend/keywords.json`의 `health_q5_codes`와 회귀 테스트로 관리한다. E78처럼 목록 밖 코드는 AI가 언급해도 Q5로 올리지 않는다.

### 2026-06-16 Anorectal Codes Are Q5 Insurance-Only

Decision:
K60, K61, K62, K64 직장·항문 질환은 Q5에만 단독 표시될 때 실손의료비보험 가입 시에만 고지 안내를 붙인다. (BOHUMFIT-039)

Reason:
직장·항문 질환은 Q5 코드목록에는 포함하되, 일반 사망·질병 고지와 실손 고지의 문맥을 구분해야 한다.

Impact:
해당 코드가 Q3 통원 등 일반 고지 항목에도 동시에 잡히면 실손 전용 안내를 붙이지 않는다. K63은 Q5 코드풀에서 제외한다.

### 2026-06-22 Phone Verification Level

Decision:
휴대폰 본인인증은 번호 입력 + /auth/verify-phone upsert 확인 수준으로 운영한다.
통신사 PASS 등 외부 본인인증 API는 연동하지 않는다.

Reason:
외부 본인인증 API 미연동 상태에서 번호 중복 hard block(088)이 신규 가입을 막는 버그 발생.
현 단계에서는 번호 소유 확인 수준으로 충분하다.

Impact:
phone_verified는 /auth/verify-phone upsert 완료 시 true 처리.
번호 중복 409 hard block 제거. 1인 1계정 원칙은 이메일 기준으로 유지.
DB 부분 UNIQUE 인덱스(profiles_phone_verified_unique) 제거 필요(Human SQL).

## Template

### YYYY-MM-DD Decision Title

Decision:

Reason:

Impact:
