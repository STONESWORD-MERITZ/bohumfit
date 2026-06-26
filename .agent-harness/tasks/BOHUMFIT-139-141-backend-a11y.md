# BOHUMFIT-139-141 백엔드 P1 2종 + 접근성 후속
## 139 처방 PDF 오분류 보정
- pdf_parser 타입 판별(헤더 강신호→page_ftype→detect_file_type) 중 헤더 OCR 누락+표제어 없을 때 본문 신호 다수결 보정.
- 처방 신호: 약품명·성분명·투약일수·1일투여횟수·처방조제 / 기본: 주상병·상병코드·입원·외래·진료일수 / 세부: 진료내역·코드명·초진·재진.
- 헤더/표제어 정상 판별은 유지(실패 시에만 fallback). 회귀: 헤더없는 처방/기본 판별·정상 헤더 유지.
## 140 의존성 버전 고정
- requirements.txt 주요 패키지 == 고정(096과 중복 여부 확인). pip dry-run·pytest 회귀.
## 141 색상대비+ARIA 스윕(137c)
- text-gray-300/400 본문/안내만 500/600(placeholder·비활성·장식 제외), 아이콘 버튼 aria-label, img alt, 애매 링크 텍스트.
## 수정 금지: 분석 로직/상태·placeholder/disabled 색상·외부 라이브러리·requirements 외 백엔드 버전.
## 완료: pytest/tsc/build, 139 신규 테스트, 140 고정, 141 개선, handoff 통합.
