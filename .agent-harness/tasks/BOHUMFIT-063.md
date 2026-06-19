# BOHUMFIT-063 레이트리밋 키 전환 — user id 기준 + IP fallback

## Owner
- Cowork (구현+회귀) → Codex (Windows 전체 검증·커밋·푸시) → Human (필요 시 위조토큰 신뢰경계 승인)

## 배경 (BF-03 + 060 후속)
- 060에서 레이트리밋·한국어 429 완료(analyze 5/min·30/h, report 10/min·60/h). 단 키=`get_remote_address`(IP).
- 문제1(오작동): Railway 프록시 뒤 여러 사용자가 같은 프록시 IP → 한 명이 한도 쓰면 전체 throttle.
- 문제2(보안): 클라이언트 X-Forwarded-For 위조 시 우회 가능.
- 확정 사양(Human): 인증=Supabase user id 키, 비인증=IP fallback.

## STEP 0 진단
- 키 설정: `limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])`(main.py L184).
- 인증 흐름: `verify_jwt`(L368)가 **Supabase Auth 서버에 httpx GET /auth/v1/user**로 검증 → 무거운 네트워크 호출이며 **엔드포인트 의존성**으로 실행(key_func보다 늦음). 즉 key_func 시점엔 verify된 user_id 없음.
- 단 Supabase 액세스 토큰은 **JWT**(payload에 `sub`=user uuid) → key_func에서 **서명검증 없이 payload만 base64url 디코드**해 sub 추출 가능(네트워크·DB 0).
- `get_remote_address`=`request.client.host`(X-Forwarded-For 미파싱). 프록시 뒤에선 프록시 IP → 충돌 원인.

## STEP 1·2 구현 (backend/main.py)
- `import base64, json` 추가.
- 신규 `_ratelimit_key(request)`:
  - `Authorization: Bearer <jwt>` → `parts=jwt.split(".")`, `parts[1]`(payload) base64url 패딩 보정 후 디코드 → `claims["sub"]`. sub(str) 있으면 **`user:{sub}`**.
  - 토큰 없음/`Bearer ` 아님/segment≠3/base64 깨짐/non-JSON/sub 없음 등 **모든 예외 → IP fallback `ip:{get_remote_address}`**(try/except 전체 감쌈, 크래시 0).
  - **경량**(서명검증·네트워크·DB 없음, payload 디코드만). 실제 인증·권한은 기존 `verify_jwt`가 담당 — 키는 식별자 용도뿐.
- `Limiter(key_func=_ratelimit_key, ...)`로 교체. **한도(analyze 5/min·30/h·report 10/min·60/h)·429 한국어 핸들러(060) 유지**.

## 회귀 테스트 (신규 tests/test_ratelimit_key_063.py, 6)
- ① 유효 Bearer(sub)→`user:{sub}`(대소문자 무관) ② 토큰 없음→`ip:{addr}` ③ malformed 8종(점없음·2seg·base64깨짐·non-JSON·sub없음·빈토큰·Basic·빈헤더)→IP fallback·크래시 0 ④ 같은 IP·다른 user→키 분리(+같은 user·다른 IP→동일 키) ⑤ `limiter._key_func is _ratelimit_key`+429 한국어 유지 ⑥ key_func가 verify_jwt(네트워크) 미호출.
- `slowapi/fastapi` importorskip(미설치 자동 skip→Codex).

## 검증
- /tmp(마운트 복구: main.py 실 tail 재구성·pdf_parser splice·surgery_exclusions/report_pdf stub)+slowapi/multipart 설치 → **TestClient/직접호출로 실제 main.py 검증: 063 6/6 + 060 9/9 + launch 2/2 = 17 passed·회귀 0**.
- ⚠ 마운트 손상(main.py byte-cap 23892·pdf_parser/report_pdf — 063 무관)→전체 pytest는 Codex/Windows. 실파일 Read로 편집 정합 확인.

## 자체 점검
- ☑ 인증→user id 키 ☑ 비인증/malformed→IP fallback·크래시 0 ☑ 같은 IP 다른 user→throttle 분리 ☑ 060 한도·429 한국어 유지 ☑ key_func 경량(DB·네트워크 0) ☑ 분석/파싱/result_builder 무변경 ☑ 가용 pytest 회귀 0.

## Notes — Human 확인
- **위조토큰 신뢰경계**: key_func는 sub를 **서명검증 없이** 키로만 사용. 공격자가 남의 sub를 위조 토큰에 넣으면 **그 사용자의 레이트리밋 한도를 소모**시킬 수 있음(경미한 사용자별 DoS). **권한 상승 아님**(실제 인증은 verify_jwt가 Supabase 서버 확인). 사양상 허용 위험이나, 우려 시 key_func에서 서명검증(JWKS) 추가 가능 — **Human 판단**.
- **X-Forwarded-For/IP fallback**: fallback은 `get_remote_address`(client.host) 유지. analyze·report는 인증 필수라 정상 트래픽은 전부 user 키 → fallback은 비인증(=401 처리) 엣지케이스. 프록시 실클라이언트 IP 신뢰 파싱은 Railway 프록시 신뢰 경계 확정 후 별도 검토(위조 방지 위해 임의 XFF 신뢰 미도입).

## Next
- **Codex(Windows)**: 전체 pytest(기준선 353 + 신규 6)·tsc/lint/build → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-063: 레이트리밋 키 user id 기준 전환 + IP fallback(프록시 공유 IP throttle 해소)`.
- **Human**: 위조토큰 신뢰경계(서명검증 추가 여부)·프록시 IP 신뢰 정책 판단.
