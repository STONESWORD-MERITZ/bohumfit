# brand/ — 브랜드 에셋 정본(소스 마스터)

이 폴더는 BohumFit(핏히어 패밀리) 브랜드 에셋의 **정본(소스 마스터)**입니다. 편집·다양한 포맷/사이즈 원본을 여기서 관리합니다.

- **정본**: `brand/` (이 폴더) — 로고·favicon·아이콘 마스터.
- **배포본**: `public/` — 앱이 실제 참조하는 정적 파일(favicon.svg, og-image.svg 등). 앱 참조는 항상 `public/`(루트 `/…`)을 가리킵니다.

새 아이콘/파비콘은 여기서 마스터를 갱신한 뒤 `public/`로 내보내고 `index.html` 참조를 맞춥니다.
근거: `.agent-harness/decisions.md` "Brand Assets: Source Master vs Deployed".
