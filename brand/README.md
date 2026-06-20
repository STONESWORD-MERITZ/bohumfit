# brand/ — 브랜드 에셋 정본(소스 마스터)

이 폴더는 BohumFit(핏히어 패밀리) 브랜드 에셋의 **정본(소스 마스터)**입니다. 편집·다양한 포맷/사이즈 원본을 여기서 관리합니다.

- **정본**: `brand/` (이 폴더) — 로고·favicon·아이콘 마스터.
- **배포본**: `public/` — 앱이 실제 참조하는 정적 파일(favicon.svg, og-image.svg 등). 앱 참조는 항상 `public/`(루트 `/…`)을 가리킵니다.

새 아이콘/파비콘은 여기서 마스터를 갱신한 뒤 `public/`로 내보내고 `index.html` 참조를 맞춥니다.
근거: `.agent-harness/decisions.md` "Brand Assets: Source Master vs Deployed".

## 운영 규칙

1. 앱 코드는 `brand/` 파일을 직접 import하지 않는다. 런타임 참조는 `public/` 배포본만 사용한다.
2. 원본 로고, favicon, 앱 아이콘을 수정할 때는 먼저 `brand/` 정본을 갱신한다.
3. 정본에서 `public/`로 내보낸 뒤 `index.html`, `site.webmanifest`, OG 이미지 참조가 맞는지 확인한다.
4. 파비콘·앱 아이콘은 그린 엠블럼을 유지하고, 헤더·푸터·로그인 워드마크는 텍스트 락업을 사용한다.
5. 배포 전 `npm run build`와 브라우저 탭 favicon/홈 아이콘 육안을 확인한다.

## 배포 체크리스트

- [ ] `brand/` 정본 파일명과 색상(`#15663D`) 확인
- [ ] `public/favicon.svg`, `favicon.ico`, `favicon-16.png`, `favicon-32.png`, `apple-touch-icon-180.png`, `icon-192.png`, `icon-512.png` 갱신
- [ ] `public/site.webmanifest`의 `name`, `short_name`, `theme_color` 확인
- [ ] `index.html`의 favicon, apple-touch-icon, manifest, theme-color 링크 확인
- [ ] `npm run build`
- [ ] 배포본 브라우저 탭·모바일 홈아이콘 육안 확인
