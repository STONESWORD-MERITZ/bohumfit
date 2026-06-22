# BOHUMFIT-100-header-logo-text

## 목표
헤더 왼쪽 로고 영역 수정:
- [F] 아이콘 이미지 제거
- 텍스트를 "BOHUMFIT 보험핏" 으로 변경

## 작업 범위
- src/components/Logo.tsx 또는 헤더 로고가 있는 컴포넌트
- src/components/ 또는 src/pages/ 내 헤더 레이아웃 파일

## 수정 지침
- [F] 아이콘(이미지 태그 또는 SVG 인라인) 제거
- 텍스트 표기: BOHUMFIT 보험핏
  - "BOHUMFIT" — 기존 폰트/색상 유지
  - "보험핏" — 같은 줄, 한 칸 띄우고, 동일 색상 또는 약간 작은 크기(text-sm 또는 text-xs)
- 예시: <span className="font-extrabold">BOHUMFIT</span>
         <span className="ml-1 text-sm font-semibold">보험핏</span>

## 비목표
- 헤더 레이아웃 전체 변경
- 색상 시스템 변경

## 완료 조건
- [x] [F] 아이콘 제거
- [x] "BOHUMFIT 보험핏" 텍스트 표시
- [x] tsc 통과
- [x] 빌드 통과
