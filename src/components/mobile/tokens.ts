// BOHUMFIT-265 — 모바일 디자인 토큰의 TS 정본(수치·규칙). CSS 변수(`index.css` @theme)와 1:1.
//   ★공통 컴포넌트는 이 상수만 참조한다(하드코딩 금지). 화면 적용은 266~.

/** 타이포 3단 — 화면 제목 / 본문(고객 가독 최소) / 보조(하한선). */
export const MOBILE_TYPO = {
  title: { px: 20, lineHeight: 1.35, weight: 700 },
  /** 본문은 16px 미만으로 내리지 않는다(40~50대 고객 가독). */
  body: { px: 16, lineHeight: 1.65 },
  /** ★보조 텍스트 하한선 — 이보다 작은 회색 본문은 금지(가드 테스트가 막는다). */
  sub: { px: 15, lineHeight: 1.55 },
} as const;

/** ★15px 미만 회색 본문 금지 — 가드가 참조하는 단일 기준값. */
export const MIN_BODY_FONT_PX = 15;

/** 터치 — 주요 액션 56 / 탭 영역 44. 시각 크기와 무관하게 히트 영역 기준. */
export const MOBILE_TOUCH = {
  action: 56,
  tap: 44,
} as const;

/** 간격·반경 — 화면 좌우 20 / 카드 20 · 버튼 15 · 배지 8. */
export const MOBILE_LAYOUT = {
  gutter: 20,
  radiusCard: 20,
  radiusBtn: 15,
  radiusBadge: 8,
} as const;

/**
 * 색 규칙 — FIT 팔레트 유지.
 *  ★라임(#CEF17B)·그린티(#CDEDB3)는 **면 전용**: 글자색·테두리색으로 쓰지 않는다(대비 1.3:1).
 *  ★장식 그라디언트 금지 — 배경은 단색 면 + 헤어라인 보더로만 구분한다.
 */
export const SURFACE_ONLY_COLORS = ["#CEF17B", "#CDEDB3"] as const;
export const GRADIENT_ALLOWED = false;

/** 상태 면(신설) — 배지·행 배경 전용. 글자는 대비가 확보된 기존 토큰을 쓴다. */
export const STATE_SURFACES = {
  warning: "var(--color-surface-warning)",
  review: "var(--color-surface-review)",
  muted: "var(--color-surface-muted)",
} as const;

/**
 * 고지 배지 4단 — ★장기 고지 배지는 **10년** 기준으로 Human 확정(초기 검토안에서 상향).
 *  라벨·면·톤을 한 곳에서 정의해 화면마다 다르게 쓰이는 것을 막는다.
 */
export const DISCLOSURE_BADGES = {
  major10y: { label: "고지대상 · 10년", surface: "warning" },
  minor3m: { label: "고지대상 · 3개월", surface: "warning" },
  review1y: { label: "검토 · 1년 재검사", surface: "review" },
  none: { label: "해당없음", surface: "muted" },
} as const;
export type DisclosureBadgeKey = keyof typeof DISCLOSURE_BADGES;

/**
 * 토스트 — 되돌리기 액션 포함 시 6초.
 *  ★남용 금지: 되돌리기 토스트는 **해지 확정 · 복사 완료 · 분석 완료 3곳만** 사용한다.
 *   (그 외 알림은 기존 `useToast`의 3초 토스트를 쓴다 — 화면마다 토스트가 쌓이면 아무도 읽지 않는다.)
 */
export const UNDO_TOAST_MS = 6000;
export const UNDO_TOAST_ALLOWED_SCOPES = ["cancel-confirm", "copy-done", "analysis-done"] as const;
export type UndoToastScope = (typeof UNDO_TOAST_ALLOWED_SCOPES)[number];

/** 스와이프 — 좌=해지, 우=복원. 임계값(px)을 넘겨야 확정된다(오조작 방지). */
export const SWIPE = {
  threshold: 72,
  maxTravel: 120,
} as const;
