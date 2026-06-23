# BOHUMFIT-116: 보장분석서 가이드 전산 링크·이미지 보강

## 목적
BOHUMFIT-115에서 추가한 보장분석서 PDF 다운로드 가이드 페이지를 실제 업무 흐름에 맞게 보강한다.

## 사용자 요청
- 가이드의 전산 주소는 보험사 링크 페이지의 전산 링크와 같은 URL을 사용한다.
- KB손보 안내에서 "MYMANAGER" 문구를 제거한다.
- 사용자가 제공한 PDF 3개를 PNG로 변환해 각 회사별 받는 방법을 이미지로도 확인 가능하게 한다.

## 입력 PDF
- `C:\Users\18_rk\Desktop\한화손보 PDF 업로드 가이드.pdf`
- `C:\Users\18_rk\Desktop\kb 분석.pdf`
- `C:\Users\18_rk\Desktop\동부손해 PDF 업로드 가이드.pdf`

## Scope
- `src/pages/CoverageGuide.tsx`
- `public/images/coverage-guide/` 신규 PNG 자산
- `.agent-harness/tasks/BOHUMFIT-116-coverage-guide-links-images.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Non-goals
- 보험사 링크 페이지 데이터 구조 개편 금지
- 타사 로고/스크린샷 신규 제작 금지
- 보장분석 파서/백엔드 변경 금지

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`

## 완료 조건
- 한화/KB/DB 전산 바로가기 버튼이 보험사 링크 페이지의 전산 URL과 동일하다.
- KB 탭에서 "MYMANAGER" 문구가 사라진다.
- PDF 3개가 회사별 PNG 이미지로 렌더링되어 CoverageGuide에서 확인 가능하다.
- 검증 통과 후 커밋·푸시한다.
