# BOHUMFIT-089 가이드 이미지 연결

## Goal
084에서 만든 DownloadGuide.tsx의 플레이스홀더를 실제 가이드 이미지로 교체한다.

## Source
C:\Users\18_rk\BOHUMFIT\guide-images\ 에 12장 준비됨:
- hira-1-menu, hira-2-login, hira-3-basic, hira-4-detail,
  hira-5-prescription, hira-6-auto-basic, hira-7-auto-detail (7장)
- nhis-1-search, nhis-2-keyword, nhis-3-service, nhis-4-overview, nhis-5-result (5장)
※ 확장자는 직접 확인 필요 (png 또는 jpg)

## Scope
- src/pages/DownloadGuide.tsx (이미지 경로 교체)
- public/images/guide/ (이미지 파일 복사)

## Out of Scope
- 다른 페이지, 다른 컴포넌트 수정 금지
