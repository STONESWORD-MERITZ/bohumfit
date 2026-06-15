# Decisions

Record durable project decisions here. Keep entries short and dated.

### 2026-05-30 Codex-Only Harness

Decision:
BOHUMFIT work will proceed with Codex as the single working agent by default.

Reason:
The previous Claude/Cowork -> Codex verification sequence created unnecessary handoff overhead.

Impact:
Codex owns implementation, verification, handoff notes, scoped staging, commit, and push when the user requests publication. Historical Claude/Cowork entries remain archival context only.

### 2026-05-30 Deterministic Disclosure Results

Decision:
For identical input PDFs and the same reference settings, disclosure-deterministic fields must be stable across repeated runs.

Reason:
The user observed that running the same materials repeatedly can change disclosure results, which breaks trust in the rule engine.

Impact:
Disease code, disease name, counts, question classification, and deterministic evidence must not change run-to-run. AI-assisted extra-exam/recheck opinion text may vary, but it must not mutate deterministic disclosure counts or disease identity.

### 2026-06-15 Brand Assets: Source Master vs Deployed

Decision:
`brand/` (repo root) = 정본(소스 마스터)이다. 배포본(앱이 실제 참조하는 파일)은 `public/`에 둔다. 앱의 favicon/아이콘/og 참조는 항상 `public/`(루트 `/…` 경로)을 가리키며, `brand/`를 직접 참조하지 않는다.

Reason:
정본(편집용 원본·다양한 포맷/사이즈)과 배포본(런타임 정적 제공)을 분리해, 디자인 변경은 `brand/`에서 하고 `public/`로 내보내 배포 일관성을 유지하기 위함.

Impact:
- `index.html`/메타 참조는 `public/favicon.svg`·`public/og-image.svg` 등 `public/` 자산만 가리킨다(확인됨).
- 새 아이콘/파비콘은 `brand/`에서 마스터를 갱신 후 `public/`로 내보내 참조한다.
- `brand/`의 미배포 자산(favicon.ico, favicon-16/32.png, apple-touch-icon-180.png 등)을 쓰려면 `public/`로 복사하고 `index.html`에 링크를 추가하는 별도 작업이 필요하다.

## Template

### YYYY-MM-DD Decision Title

Decision:

Reason:

Impact:
