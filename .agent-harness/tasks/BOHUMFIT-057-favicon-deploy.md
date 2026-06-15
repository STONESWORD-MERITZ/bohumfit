# BOHUMFIT-057 리브랜딩 파비콘 세트 public 배포

## Owner
Codex 단독(Windows 검증·git)

## Goal
`brand/` 정본 favicon/icon 세트를 `public/` 배포본으로 내보내고, `index.html` head 링크와 web manifest를 정리한다.

## Scope
- `public/favicon.ico`
- `public/favicon-16.png`
- `public/favicon-32.png`
- `public/apple-touch-icon-180.png`
- `public/icon-192.png`
- `public/icon-512.png`
- `public/favicon.svg`
- `public/site.webmanifest`
- `index.html`
- 하네스 task/handoff/locks

## Steps
1. `brand/`에서 지정 에셋을 `public/`로 복사한다.
2. `public/favicon.svg`는 `brand/fithere-logo.svg` 고정 그린 엠블럼으로 덮어쓴다.
3. `index.html` head에 ico/png/svg/apple-touch/manifest/theme-color 링크를 둔다.
4. `site.webmanifest`에는 `name`/`short_name`을 `보험핏`, theme color를 `#15663D`로 둔다.

## Verify
- `npm run build`
- `npm run preview`에서 파비콘/manifest 응답 및 탭 파비콘 엠블럼 육안 확인
- `dist/`에 favicon·icon·manifest 포함 확인
