# BOHUMFIT-130 수술 감지 로직 강화
## 배경
세부진료 수술 판정 오분류(수술O인데 X, 수술X인데 O) 보완 + 동일 논리 선제 확장.
## 확정 스펙
- 수술X(제외 추가): 자궁경부약물소작술·갑개소작술·비인강소작술·인후두소작술 / 신경차단술·신경차단.
- 수술O(포함 추가): 유치카테터(유치도뇨관 포함)·티눈 냉각응고술·후궁성형술·신경성형술.
## Step1 분석(현행)
- surgery_exclusions.py: _STRONG(강수술·있으면 수술유지)·_NON_SURGERY_ACTION(비수술·부분일치)·NON_SURGERY_NAMES(완전일치). is_non_surgery_excluded가 _is_surgery_match/_is_detail_surgery_match를 가드.
- 양성 감지: keywords.json surg_keywords(_is_surgery_match) + disease_aggregator _DETAIL_CONFIRMED_SURGERY_KEYWORDS + nhis_surg_keywords. detail은 _is_detail_support_only(카테터 등)→_is_detail_surgery_match.
- 답: 1)소작=surg_keywords 'soa작' 양성→현재 수술O(오분류) 2)신경차단=미감지지만 처치및수술 컬럼이면 수술(오분류) 3)유치도뇨관=현재 '도뇨'로 비수술 제외(오분류, 수술X) / 유치카테터=미감지+'카테터' support-only 가드 / 냉각응고술=미감지 / 성형술=_DETAIL_CONFIRMED로 detail 감지됨 4)action·strong=부분일치, NON_SURGERY_NAMES=완전일치.
## Step2 확장 후보
- 수술X 추가: 소작(전기/약물/레이저소작 포괄)·약물소작·신경차단·도포(약물 도포).
- 수술O 추가: 유치카테터·유치도뇨·냉각응고술(_DETAIL_CONFIRMED). 성형술/절제술/봉합술은 이미 _DETAIL_CONFIRMED로 감지(누락 없음).
## Step3 수정
- surgery_exclusions.py: _NON_SURGERY_ACTION += 소작·약물소작·신경차단·도포 / _STRONG += 유치카테터·유치도뇨('도뇨' 제외 override).
- disease_aggregator.py: _DETAIL_CONFIRMED += 유치카테터·유치도뇨·냉각응고술 / _is_detail_support_only에서 '유치' 포함은 support-only 예외(유치카테터 가드 해제).
## Step4 검증: pytest 전체 + 신규(a 수술X 6항목 / b 수술O 4항목 / c 기존 수술 정상 / d Step2).
## 수정 금지: filters.py 임계값·범위 외·프런트.
