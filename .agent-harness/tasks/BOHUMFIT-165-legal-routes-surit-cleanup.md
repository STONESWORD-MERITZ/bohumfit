# BOHUMFIT-165 — 법무 공백 마감 + 404/URL 통일 + before-after 제거 + SURIT 잔재 삭제

## 배경
BOHUMFIT-148 감사 보고서의 Human 승인 4건(보고서 ID 155·152·161·153) 통합 실행.
Human 결정: 법무 이메일=qqqwe6701@gmail.com / before-after 제거 / terms·privacy 정본 통일 / SURIT 잔재 삭제(bohumfit.ai 완전 이전 전제).

## 수정 금지
- 고지의무 분석 파이프라인(backend/pipeline/ 일체)
- /coverage(CoverageAnalysis) — 유지 결정, 무접촉
- 범위 외 페이지 스타일/토큰 변경(149·150 별도)

## Part A — 법무 연락처(보고서 155, P0)
- PrivacyPolicy.tsx 보호책임자 연락처 "이메일 추가 예정" → qqqwe6701@gmail.com, 임시 공지문구 제거.
- Footer.tsx 고객센터 "이메일 추가 예정" → qqqwe6701@gmail.com + mailto 링크.
- TermsOfService.tsx 문의처 미확정 시 동일 이메일로 통일.

## Part B — 404 + URL 통일(보고서 152)
- NotFound.tsx 신설(토큰, "페이지를 찾을 수 없습니다" + 홈 버튼), App.tsx catch-all `path="*"`.
- Signup.tsx `/terms`→`/terms-of-service`, `/privacy`→`/privacy-policy`. src/ 별칭 직접링크 0 확인.
- `/terms`·`/privacy` 라우트는 정본으로 redirect(Navigate replace) 전환. Terms.tsx(shim) 삭제 + import 정리.

## Part C — before-after 제거(보고서 161)
- App.tsx `/before-after` 라우트 + 인라인 BeforeAfterComingSoon + 관련 import 삭제. 참조 0 확인.

## Part D — SURIT 잔재 삭제(보고서 153)
- backend/main.py CORS 기본 오리진에서 surit-react.vercel.app 제거(bohumfit.ai 유지).
- .env.example SURIT 값 → BOHUMFIT/bohumfit.ai 갱신.
- vercel.json 운영 API URL이 아직 surit 도메인이면 ⚠변경 금지·handoff 보고만(Railway 실주소=Codex/Human).
- AGENTS.md SURIT 표기 → BOHUMFIT 갱신.
- repo 전체 `-i surit` grep 결과 handoff 기록(잔여 0 목표, 불가피 잔여 사유 명시).

## 검증(샌드박스)
- PrivacyPolicy·Footer "추가 예정" 0 / src/ `/terms`·`/privacy` 별칭 직접링크 0(redirect 제외) / before-after 참조 0 / repo `-i surit` grep 기록.
- tsc/build/pytest = Codex/Windows 권위.

## 커밋(Codex)
fix(BOHUMFIT-165): 법무 연락처 확정 + 404/URL 통일 + before-after 제거 + SURIT 잔재 정리
