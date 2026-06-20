# BOHUMFIT-082-korean-typography
## 목적
한국어 모바일 UI 타이포그래피 최적화.
한글이 글자 단위로 어색하게 끊기지 않고,
제목/본문/버튼/카드/textarea가 모바일에서 깔끔하게 보이도록 개선.
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- src/index.css (전역 타이포그래피 규칙 추가)
- src/pages/Home.tsx (ko-heading, ko-text 클래스 적용)
- src/pages/DownloadGuide.tsx (ko-heading, ko-text 클래스 적용)
- src/pages/Subscription.tsx (ko-heading, ko-text 클래스 적용)
- src/pages/Disclosure.tsx (ko-text, ko-textarea 클래스 적용)
## 완료 조건
- word-break: keep-all 전역 적용 (break-all 금지)
- 제목: text-wrap balance + line-height 1.28
- 본문: text-wrap pretty + line-height 1.62
- 긴 URL/영문/코드: safe-break 예외 클래스
- textarea: line-height 1.6, padding 14-16px
- iPhone SE/14/15, Galaxy S 기준 확인
