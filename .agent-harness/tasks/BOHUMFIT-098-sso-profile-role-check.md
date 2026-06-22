# BOHUMFIT-098-sso-profile-role-check

## 배경
fithere ↔ bohumfit SSO 통합으로 bohumfit Supabase가 마스터가 됨.
fithere 측에서 아래 변경이 이미 적용됨:
- profiles.role: text → user_role enum ('user' → 'customer' 매핑)
- handle_new_user 트리거: fithere 버전으로 교체
  (full_name, avatar_url, updated_at 컬럼 추가)

## 목표
bohumfit 코드에서 위 변경으로 인한 영향 점검 및 수정

## 점검 항목

### 1. role 비교 코드
- 전체 코드에서 role === 'user' 또는 role === "user" 검색
- 발견 시 role === 'customer' 로 수정
- role을 INSERT하는 부분도 확인 (기본값 'user' → 'customer')

### 2. profiles SELECT/INSERT 충돌 확인
- profiles 테이블을 SELECT하는 코드에서
  full_name, avatar_url, updated_at 컬럼 추가로 인한 영향 확인
- TypeScript 타입 정의에 해당 컬럼 추가 필요 시 추가
- INSERT 시 충돌 없는지 확인

### 3. handle_new_user 트리거 교체 영향
- 신규 가입 시 profiles 자동 생성 로직이 트리거로 이동됨
- bohumfit 코드에서 가입 직후 profiles를 직접 INSERT하는 부분 있으면
  트리거와 중복 INSERT 충돌 여부 확인
- 중복이면 코드 측 INSERT 제거

## 비목표
- fithere 코드 수정
- Supabase 마이그레이션 직접 실행
- NICE 본인인증 연동

## 완료 조건
- [ ] role 비교 코드 전수 점검 및 수정
- [ ] profiles 타입 정의 업데이트
- [ ] 트리거 중복 INSERT 없음 확인
- [ ] tsc 통과
- [ ] 검증 통과
