# BOHUMFIT-088: 휴대폰 번호 중복가입 임시 방어 (실본인확인 전 단계)
## 목적
실제 본인확인 연동(087) 전이라도, 동일 휴대폰번호로 복수 계정이 인증 완료되는 것을 임시로 막는다.
## 한계(문서화)
- 스텁은 사용자가 번호를 직접 입력 → 다른 번호 입력 시 우회 가능. 본 태스크는 "동일 번호 재사용"만 차단하는 임시방편. 진짜 1인1계정은 087(CI 기반)에서 완성.
## 대상 파일(정확 경로는 확인 후)
- supabase/migrations/20260620000004_phone_unique.sql (신규)
- src/pages/PhoneVerify.tsx (중복 시 사용자 안내)
- backend/main.py verify-phone (중복 시 명확한 에러 응답)
## 요구사항
1. 마이그레이션(신규, 멱등):
   - profiles.phone에 부분 UNIQUE 인덱스: phone_verified=true 이고 phone IS NOT NULL 인 행에 한해 phone 유일.
     (예: create unique index ... on profiles(phone) where phone_verified = true and phone is not null;)
   - 이미 중복 데이터가 있으면 인덱스 생성 실패 가능 → 그 경우를 주석으로 안내(Human이 중복 정리 후 재실행). 실행은 Human.
2. backend verify-phone:
   - upsert 전, 동일 phone으로 phone_verified=true인 "다른 user" 존재 여부 확인.
   - 있으면 409(또는 명확한 코드)와 한국어 메시지("이미 인증에 사용된 번호입니다") 반환. internal 역할은 예외.
3. PhoneVerify.tsx:
   - 중복 에러 응답을 받으면 사용자에게 한국어 안내 표시(중복 번호 안내·문의 유도). 정상 성공 흐름은 086 그대로.
## 정책
- internal 역할은 중복 검사 우회(기존 우회 정책과 일관).
## 비범위
- CI 기반 동일인 판별(087 영역), 번호 변경 플로우.
## 검증
- npx tsc app/node / npm run lint / npm test / cd backend && python -m pytest -q / npm run build(기존 chunk size warning만)
- backend 중복검사 분기 단위 테스트 추가/보강.
