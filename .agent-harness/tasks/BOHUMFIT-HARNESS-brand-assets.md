# BOHUMFIT-HARNESS-brand-assets 브랜드 에셋 거버넌스(정본 brand/, 배포본 public/)

## Owner
Cowork(샌드박스 문서 작업) → Codex(Windows 검증·커밋·푸시). 코드 무변경(문서만).

## 목표
브랜드 에셋의 정본/배포본 위치 규칙을 decisions.md에 못박고, favicon/아이콘 참조가 배포본(public/)을 가리키는지 확인한다.

## 수행
1. favicon/아이콘/og 참조 경로 grep(index.html·public/): 참조가 public/(루트 `/…`)을 가리키는지 확인. `brand/` 직접 참조면 handoff 경고.
2. `.agent-harness/decisions.md`에 결정 추가: "brand/ = 정본(소스 마스터), 배포본은 public/".
3. (선택) `brand/README.md` 1줄 작성(정본 안내).

## 검증
- 코드 무변경 → tsc/test 불필요(사유 handoff). 필요 시 `npm run build`로 favicon 산출 확인만(public/는 정적 복사라 빌드 영향 없음).
- 마운트 git 금지 → stage/commit/push는 Codex(Windows).

## 산출
- handoff: 참조 경로 확인 결과·정본/배포본 규칙·미배포 에셋 경고(있으면). Next: Codex.
