# BOHUMFIT-091 카카오톡 복사 5년 초과 창 누락 수정 (백엔드)

## 증상
- 화면·리포트: 5년 초과(1825일+)~10년(3650일) 구간 입원·수술력 정상 표시
- 카카오톡 복사하기: 해당 구간 누락

## 진단 (BOHUMFIT-090에서 확정)
- 카카오 텍스트는 backend/main.py의 _build_kakao_message()가 생성
- 화면/리포트는 standard_reports를 직접 렌더링 (정상)
- 카카오는 std_reports 기반 _build_kakao_message()를 별도 경유 (누락 발생)
- 프런트 handleCopy는 백엔드 문자열을 그대로 writeText할 뿐 (무관)

## Scope
- backend/main.py (_build_kakao_message 및 관련 함수)
- backend/tests/test_kakao_window.py (신규 회귀 테스트)

## Out of Scope
- 프런트 무변경
- 다른 백엔드 파일 무변경
