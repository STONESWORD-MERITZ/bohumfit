# BOHUMFIT-156b — 분석 히스토리 프런트 (저장·목록·재열람)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork
선행: BOHUMFIT-156a (백엔드 API)

## Intent
- 분석 완료 후 결과를 별칭으로 저장하고, /history에서 목록·재열람·삭제할 수 있게 한다.
- 실명 저장 금지 안내와 90일 보관 고지로 개인정보 리스크를 낮춘다.

## Step 0 — 진단 (handoff 기록)
- Disclosure.tsx 결과 렌더에 히스토리 JSON 주입으로 재열람 가능한지 판단.
- 대수술이면 이번 범위는 저장+목록까지, 재열람은 156c 후속 제안으로 축소 (근거 handoff 기록).

## Step 1 — 저장 UX
- 분석 완료 화면에 "히스토리에 저장" 세컨더리 버튼 (라임 CTA 금지)
- label 모달: "고객 실명 대신 별칭을 입력하세요" 안내 + 보관 90일 1줄 고지
- 409 응답 시 Pro 안내 인라인 1줄 (과하지 않게)

## Step 2 — 목록/재열람
- 신규 /history (ProtectedRoute), DisclosureHub에서 진입 링크 (NAV 편입 안 함)
- 목록: label·mode·날짜·삭제(확인 모달)·빈 상태
- 재열람: Step 0 판단대로

## Step 3 — 법무 (필수)
- PrivacyPolicy.tsx에 보관 조항 추가: 항목(별칭·분석 결과)·90일·삭제권·자동 파기

## Scope
- 수정 허용: src/pages/History.tsx(신규), src/App.tsx, src/pages/DisclosureHub.tsx, src/pages/Disclosure.tsx, src/pages/PrivacyPolicy.tsx
- 수정 금지: backend 전체 / 분석 실행 흐름 (결과 렌더 재사용 최소 분리는 허용)
- 스타일: FIT v1.1 토큰만 사용 (raw gray 0)

## Verification
- grep: 신규/수정 파일 raw gray 0
- tsc/build는 Codex/Windows 권위

## Handoff Requirements
- Step 0 진단 결과(재열람 방식 판단 근거) 기록
