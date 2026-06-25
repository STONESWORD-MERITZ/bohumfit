# BOHUMFIT-122: KB 가이드 이미지 하단 텍스트 검정색 재작성
## 목표
KB 가이드 이미지(kb-02.png ~ kb-10.png) 9장의 하단 파란색 안내 문구를 흰색으로 덮고,
동일 크기 검정색(#000000) Bold 텍스트로 재작성한다.
## 위치
- 원본: `public/images/coverage-guide/kb-02.png ~ kb-10.png` (dist/는 build 산출물 — 미수정)
- 캡션은 스크린샷 아래 흰 여백에 위치(파란 Bold·중앙정렬). 스크린샷 내부 파란 UI는 보존.
## 기준
- 폰트 크기: kb-08 하단 문구와 동일(스크립트가 kb-08 캡션 높이로 폰트 크기 캘리브레이션 → 전 이미지 공통 적용)
- 색상: 검정 #000000 / 굵기: Bold(NanumGothicBold 없으면 NotoSansCJK-Bold KR)
## 구현 (Pillow, /tmp/recolor_kb.py)
1. 각 이미지 로드, 하단(y≥0.86H) 파란 픽셀(R<100,G<100,B>150) bbox 감지(=캡션, 스크린샷 파랑 제외)
2. 캡션 밴드 흰색 fill(밴드 배경이 흰색=mean>235 확인 후 폭넓게, 아니면 bbox만)
3. kb-08 캡션 높이 기준 폰트 크기 결정(NotoSansCJK-Bold) — 전 이미지 공통
4. 이미지별 고정 문자열을 검정 Bold·수평 중앙·밴드 수직 중앙으로 재작성(2줄은 \n)
5. 원본 경로 덮어쓰기(처리 전 /tmp 백업)
## 검증
- kb-02/06/08 전후 육안(파랑→검정, 잘림·이탈 없음)
- tsc(app·node)/lint/npm test/build — 이미지 자산만 변경이라 코드 무영향(Codex 권위)
## Next: Codex (이미지 육안 확인 후 커밋·푸시)
