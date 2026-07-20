# BOHUMFIT-228-C — backend pip-audit 취약점 리포트 (문서 전용 · requirements 수정 0)

Date: 2026-07-20 | 도구: pip-audit(신규 설치 — 도구만, backend 의존성 설치·업그레이드 0)
실행: `PYTHONUTF8=1 python -m pip_audit -r <file> --no-deps` (requirements가 전부 고정 버전이라 --no-deps 가능.
※기본 실행은 한국어 주석의 cp949 오디코딩으로 실패 — PYTHONUTF8=1 우회, 파일 무수정)

## 결과 요약

- `backend/requirements.txt`: **11건 / 2패키지**
- `backend/requirements-dev.txt`: **0건** ✓

## 취약점 목록 (requirements.txt)

| 패키지 | 현재 버전 | 취약점 ID | 수정 버전 |
| --- | --- | --- | --- |
| pillow | 12.2.0 | PYSEC-2026-2253 · 2254 · 2255 · 2256 · 2257 · 3451 · 3452 · 3453 (8건) | **12.3.0** |
| python-multipart | 0.0.29 | PYSEC-2026-3036 · 3037 (fix 0.0.30) · PYSEC-2026-3040 (fix 0.0.31) | **0.0.31** (3건 전부 커버) |

## 영향 평가 (참고)

- `pillow`: PDF 리포트 렌더 경로(이미지 처리)에서 사용 — 140에서 버전 고정 이력. 악성 이미지 입력면이
  제한적(서버 생성 이미지 중심)이나 업로드 PDF 파싱 체인과 인접하므로 업그레이드 권장.
- `python-multipart`: FastAPI 업로드 폼 파싱 — **사용자 업로드 직접 경로**라 상대적으로 우선순위 높음.

## 후속 태스크 제안

- **[중위험] backend 의존성 보안 업그레이드**: `pillow==12.3.0`, `python-multipart==0.0.31`로 고정 상향.
  검증: `python -m pytest -q` 618/8 기준선 + 실 PDF 렌더 스모크(pillow 경로) + 업로드 스모크(multipart 경로).
  풀 하네스(Code 구현·1차 → Codex 2차·커밋) 권장. requirements 수정이므로 이번 228 범위 밖.
- 참고: pip 25.0.1 → 26.x 업그레이드 알림 존재(도구 체인 — 필수 아님, 기록만).
