# ENV Mount Notes

SURIT-ENV-001 기준, 샌드박스 마운트와 Windows 원본 사이에는 반복 재현된 동기화 및 권한 제약이 있다. 이 문서는 마운트 환경에서 작업할 때의 회피 규칙이다.

## Known Issues

- 마운트 파일 뷰는 최초 동기화 바이트 길이로 고정될 수 있다. 이후 편집으로 파일이 커지면 그 길이에서 중간 바이트 단위로 잘릴 수 있다.
- 잘림은 `SyntaxError`뿐 아니라 UTF-8 중간 바이트 절단으로 `UnicodeDecodeError`처럼 나타날 수 있다.
- 신규 파일 최초 쓰기는 온전할 수 있지만, 기존 파일 편집이나 증가분 동기화는 신뢰하지 않는다.
- 마운트에서 파일 삭제/unlink가 권한 거부될 수 있다.
- 마운트에서 `git status` 같은 읽기성 git 명령만 실행해도 `.git/index.lock` 잔존, null sha1, 추적 파일의 `D` + `??` 오표시가 발생할 수 있다.
- 디스크의 Windows 원본 파일이 정상이어도 마운트 뷰만 잘려 보일 수 있다.

## Authority

- 검증 권위는 Windows 원본이다.
- 마운트의 `wc`, `ast.parse`, `pytest`, `tsc`, `git status` 결과가 Windows 원본과 충돌하면 Windows 원본을 우선한다.
- 마운트 truncation 의심 시 handoff에 기록하고 Codex Windows 검증으로 넘긴다.

## Rules

- Cowork/마운트 환경에서는 git 명령을 실행하지 않는다.
- `git status`, `git add`, `git commit`, `git push`, `git restore`, `index.lock` 정리는 Codex가 Windows에서만 수행한다.
- 마운트에서 테스트가 필요하면 mounted repo가 아니라 `/tmp` 같은 샌드박스 로컬 경로에 독립 스크립트를 만들어 검증한다.
- 편집 파일의 구조 및 완결성은 Windows 원본 Read/Grep 또는 Codex Windows 명령으로 확인한다.
- 대형 기존 파일 편집은 가능한 경우 신규 모듈로 분리해 마운트 동기화 리스크를 줄인다.
- 마운트에서 설정 파일이 삭제(`D`)로 보이면 실제 디스크 존재 여부를 먼저 확인하고, 커밋하지 않는다.
- 불확실하면 푸시하지 않고 handoff에 원문 증상과 "사람 확인 필요"를 남긴다.

## Recovery Checklist (Codex Windows)

- `git status --short -uall` 확인.
- `.git/index.lock`가 있으면 실제 git writer 프로세스가 없는지 확인 후 제거.
- `tsconfig*`, `vite.config.ts`, `vitest.config.ts`, `vercel.json` 등 설정 파일이 staged deletion이면 디스크 존재 확인 후 `git restore --staged <file>`로 해제.
- generated/cache 파일은 태스크 범위가 아니면 staging에서 제외한다.
- 검증 통과 후 태스크 범위 파일만 stage/commit/push한다.
