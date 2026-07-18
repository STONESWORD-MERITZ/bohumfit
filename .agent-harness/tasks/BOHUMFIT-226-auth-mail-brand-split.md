# BOHUMFIT-226-D — FitHere 인증 메일 브랜드 분리 사전조사 (조사 전용 · 코드 변경 0)

Date: 2026-07-17 | 작성: Claude Code

## 배경

BOHUMFIT·FitHere가 Supabase 인스턴스(Auth 포함)를 공유한다. Reset Password 메일 템플릿이
"보험핏" 브랜딩으로 한글화되어 있어, FitHere 이메일 로그인 사용자가 비밀번호 재설정 메일을
받으면 브랜드 혼선이 발생할 수 있다(2026-07-17 Human 확인). Supabase 메일 템플릿은
프로젝트당 1벌(유형별)이라 서비스별 브랜딩이 기본 제공되지 않는다.

## ① 저장소 내 사용처 전수 (BOHUMFIT 측 실측)

| 파일:라인 | 호출 | 메일 발송 여부 |
| --- | --- | --- |
| `src/pages/ForgotPassword.tsx:61-64` | `resetPasswordForEmail(email, { redirectTo: origin + "/reset-password" })` | ★Reset Password 템플릿 발송 — 혼선 대상 |
| `src/pages/Signup.tsx:46` | `signUp(...)` — `emailRedirectTo` 미지정 | Confirm signup 템플릿 발송(이메일 확인 활성 시) — 같은 공유 템플릿 문제에 노출 |
| `src/pages/Login.tsx:57·66`, `Signup.tsx:64` | `signInWithOAuth({ redirectTo: origin })` | 메일 발송 없음(OAuth 리다이렉트) |
| 테스트 4파일(ForgotPassword/ResetPassword/AuthCaptcha/PublicRoutesSmoke) | mock | 발송 없음 |

- FitHere 측 사용처는 이 저장소에서 실측 불가 — FitHere 레포에서 `resetPasswordForEmail`·
  `signUp`·`emailRedirectTo` 전수 grep이 후속 태스크 선행 항목이다.
- 두 서비스 모두 `redirectTo`에 자기 도메인을 넘기므로, 메일 템플릿의 `{{ .RedirectTo }}`
  (또는 ConfirmationURL의 목적지 도메인)가 어느 서비스 요청인지의 유일한 신호다.

## ② 분기 방법 비교

| 방식 | 작업량 | 위험도 | FitHere 측 필요 변경 |
| --- | --- | --- | --- |
| **1. 중립(서비스 무표기) 템플릿** — 템플릿에서 "보험핏" 고유 브랜딩 제거, "요청하신 서비스의 비밀번호 재설정" 중립 한글 문구 + 버튼 링크는 `{{ .ConfirmationURL }}` 그대로(목적지 도메인이 브랜드 신호) | 소(대시보드 문구 수정만) | 저 — 코드 0, 발송 경로 무변경. 양쪽 모두 브랜드 강화는 포기 | 없음(문구 검수만) |
| 2. Send Email Hook(Auth Hook + Edge Function) — 훅에서 `redirect_to` 도메인으로 분기해 서비스별 템플릿을 자체 SMTP/API(예: Resend)로 발송 | 중~대(함수 작성·메일 발송 수단·시크릿·실패 폴백 설계) | 중 — 훅 장애 = 양쪽 인증 메일 전체 불발 위험, 발송 도메인/SPF/DKIM 운영 필요 | 템플릿 시안 협의(코드 변경은 불필요할 수 있음) |
| 3. Supabase 인스턴스 분리 — 서비스별 프로젝트 | 대(Auth 사용자·공유 테이블 분리 이관) | 고 — 현재 아키텍처가 **의도적 공유 DB**(profiles·advisors 등 공동 사용, 218~225 전제)라 정면 충돌. 데이터 이관·이중화 비용 | 대규모(전면) |

- 참고: 템플릿은 Go 템플릿이지만 Supabase가 노출하는 변수·함수가 제한적이어서
  "템플릿 내 도메인 조건 분기"는 문서화된 지원 경로가 아니다 — 방식 1의 변형으로
  검토는 가능하나 무보증(후속 태스크에서 실험 필요 시 별도 확인).

## ③ 권장안

**단기 = 방식 1(중립 템플릿)**: 지금의 혼선(타 서비스 브랜드 노출)을 대시보드 문구 수정만으로
즉시 제거한다. 코드·훅·인프라 변경 0, 실패 모드 없음. Reset Password와 함께 Confirm signup /
Magic Link / Email Change 등 나머지 공유 템플릿도 같은 원칙으로 일괄 중립화한다.
**중기 = 방식 2(Send Email Hook)**: 서비스별 브랜딩이 사업적으로 필요해지면 훅 분기로 승급.
방식 3은 공유 DB 아키텍처와 충돌하므로 권장하지 않는다.

## 후속 태스크 명세 초안 (Chat 발번용)

- 제목: 공유 Supabase 인증 메일 템플릿 중립화
- 주체: Human(Supabase Dashboard — Auth > Email Templates), 문구는 Chat 작성·Human 검수
- 범위: Reset Password 필수, Confirm signup·Magic Link·Email Change 동시 검토
- 문구 원칙: 서비스명 무표기 중립 한글, 버튼/링크는 기존 변수 유지, 피싱 오인 방지를 위해
  "요청하지 않았다면 무시" 안내 유지
- 선행 확인: FitHere 레포 `resetPasswordForEmail`/`emailRedirectTo` 전수 grep,
  FitHere reset 랜딩 경로 존재 확인
- 검증: 양쪽 서비스에서 각각 재설정 메일 실수신 → 문구·링크 도메인 확인(운영 테스트 계정)
- 위험도: 저(문구만·롤백 = 이전 템플릿 복원). DB·코드 변경 0
