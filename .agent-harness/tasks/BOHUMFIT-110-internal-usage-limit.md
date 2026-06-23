# BOHUMFIT-110: internal 사용량 pro 동일(100회)로 변경
## 목표
profiles.role = 'internal' 사용자의 월 사용량 한도를
현재 무제한에서 pro 플랜과 동일한 100회로 변경한다.
## 변경 대상
### 백엔드 backend/main.py
- internal role 무제한 우회 분기를 찾아 pro 플랜과 동일하게 월 100회 한도 체크로 변경
### 프런트 src/pages/Subscription.tsx
- "내부 사용자 — 무제한 이용" 문구를 "내부 사용자 — 월 100회" 로 변경
## 검증
- npx tsc app/node / npm run lint / npm test / cd backend && python -m pytest -q
## 완료 조건
- internal 계정으로 100회 초과 시 제한 메시지 표시
- Subscription.tsx 문구 변경 확인
