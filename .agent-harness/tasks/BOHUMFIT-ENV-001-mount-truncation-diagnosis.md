# BOHUMFIT-ENV-001 — 마운트 truncation + git 인덱스 손상 진단 (환경 진단 전용)

- Owner: Cowork (진단) — 읽기/관측 전용. 저장소 코드·문서 수정 금지, git 상태 변경 금지.
- 생성: 2026-06-08
- 목적: BOHUMFIT-022~028 7회 재발한 마운트 truncation·git 인덱스 손상의 발생 조건을 통제 실험으로 수집.
- 권위 기준: **Windows 원본(Read 도구) = 권위. 마운트 뷰(bash)는 불신·대조 대상.**

## 방법
- 기존 truncated 파일: Windows(Read) vs 마운트(wc/ast.parse) 대조.
- 통제 실험: 저장소 밖 outputs 작업영역(`/sessions/.../mnt/outputs/`)에 신규 파일 생성→Edit→측정.
- git: 관측만(상태 변경·lock 제거 금지).

## 결과 요약
상세·5항목 산출물은 `.agent-harness/handoff.md` 2026-06-08 BOHUMFIT-ENV-001 항목 참조.
- 핵심: 마운트는 **최초 동기화 바이트 길이로 버퍼 고정** → 이후 편집으로 커진 내용이 그 길이에서 mid-char 잘림.
- 신규 파일(깨끗한 최초 쓰기)은 온전 동기화. 편집·증가가 문제.
- 샌드박스 bash는 마운트 파일 **삭제/unlink 불가**(권한) → git `index.lock` 정리 불가 → 인덱스 null-sha1 손상(파일 D+?? 오표시). 디스크 파일은 멀쩡, Windows git은 별개·정상.

## 산출물(/tmp·outputs 실험 잔여)
- `outputs/env_probe_new.py` — 통제 실험 잔여(삭제 불가). 저장소 밖이라 repo 미오염.

## 검증
- 코드 수정 없음. 진단 태스크 파일 + handoff 기록만. git 상태 변경 없음.
