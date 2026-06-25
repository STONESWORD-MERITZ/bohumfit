# BOHUMFIT-121: 가이드 이미지 표지 삭제 + KB MYMANAGER 문구 제거

## 목표
1. KB손보 가이드 이미지 전체에서 하단 MYMANAGER 문구 제거
2. KB 1페이지(kb-01.png) 삭제
3. DB 1페이지(db-01.png) 삭제

## 작업 상세

### 1. KB 1페이지 삭제
- `public/images/coverage-guide/kb-01.png` 삭제
- kb-02.png ~ kb-10.png가 남음 (총 9장)

### 2. DB 1페이지 삭제
- `public/images/coverage-guide/db-01.png` 삭제
- db-02.png ~ db-20.png가 남음 (총 19장)

### 3. KB 이미지 하단 MYMANAGER 문구 제거
- `public/images/coverage-guide/kb-02.png` ~ `kb-10.png` 전체 (9장)
- 각 이미지 하단의 "MYMANAGER" 및 "sales enablement system" 텍스트 영역을
  흰색 배경으로 덮어서 제거
- Python Pillow로 처리:
  - 각 이미지 하단 약 40~60px 영역을 흰색으로 fill
  - 원본 파일 덮어쓰기

### 4. CoverageGuide.tsx 이미지 인덱스 수정
- KB: 1페이지 삭제로 kb-01 제거 → kb-02~kb-10 (9장) 으로 조정
- DB: 1페이지 삭제로 db-01 제거 → db-02~db-20 (19장) 으로 조정
- 이미지 파일명 변경 없이 시작 인덱스만 조정
  (예: Array.from({length: 9}, (_, i) => `kb-0${i+2}.png`) 방식으로)

## 검증
- count check: kb 9장, db 19장 확인
- 육안 확인: kb-02, db-02 이미지 하단 MYMANAGER 문구 없음
- npx tsc -p tsconfig.app.json --noEmit
- npx tsc -p tsconfig.node.json --noEmit
- npm run lint
- npm test
- npm run build

## 커밋
검증 통과 시:
stage: public/images/coverage-guide/ (변경분), src/pages/CoverageGuide.tsx,
       .agent-harness/tasks/BOHUMFIT-121-coverage-guide-image-cleanup.md
커밋 메시지: "BOHUMFIT-121: KB·DB 가이드 표지 삭제 + KB MYMANAGER 문구 제거"
push

## handoff 기록
표준 포맷으로 상단에 추가.
Next: Human (브라우저에서 /coverage-guide KB/DB 탭 첫 이미지와 하단 문구 확인)
