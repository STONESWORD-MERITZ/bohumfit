# BOHUMFIT-138 UX 버그픽스 + 기능 추가 7종
## 항목
1. 업로드 영역 문구 숨김: 파일 선택 시 "드래그하거나 클릭" 문구 숨기고 파일명 목록만, 미선택 시 문구 유지. (Disclosure.tsx)
2. 분석 중 단계 목록 제거: AnalysisProgress.tsx 단계 ol 제거, 스피너+"분석 중입니다..." 유지.
3. 결과 화면 대각선 렌더링 버그: bf-beam(conic-gradient/mask) 원인 → 제거 또는 clip-path. (index.css/Disclosure article)
4. 질병명 띄어쓰기 강화: helpers.normalize_disease_name — \n\r 제거·공백 정규화·사전 매칭. 예 "폐 쇄에대한 언급이없 는기타담 석증"→"폐쇄에대한 언급이없는 기타담석증". 회귀 테스트.
5. 미래 날짜 경고 제거: 경고 메시지 생성/표시만 제거(레코드 제외 로직 유지). disease_aggregator date_warnings.
6. PDF 미리보기: 결과 상단, object/createObjectURL, 다중=탭, 500px, 접기/펼치기(기본 접힘), 파일 없으면 미표시.
7. 10분 재보기: sessionStorage에 result+timestamp, 로드 시 10분 이내 복원+배너(N분 전)+"새로 분석하기", 초과 시 삭제.
## 수정 금지: 분석 로직/상태·레코드 제외 로직·외부 라이브러리.
## 완료: 7항목, pytest/tsc/build, handoff 항목별 기록.
