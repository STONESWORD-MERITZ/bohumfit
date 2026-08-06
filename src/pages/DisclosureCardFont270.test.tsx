/// <reference types="node" />
// BOHUMFIT-270 — DiseaseCard 모바일 폰트 오버라이드(B안).
//
//   ★핵심 계약: ①데스크톱 폰트는 **한 픽셀도** 바뀌지 않는다(A안 미채택의 이유가 그것이다)
//   ②모바일은 265 토큰(16/15)만 쓰고 하한 15px를 지킨다(269b처럼 가드를 우회하지 않는다)
//   ③정보 계층이 뒤집히지 않는다 ④분기는 CSS가 아니라 `useIsMobile` JS 판정이고 미지원 시 데스크톱 폴백.
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DISEASE_CARD_MOBILE_TYPO,
  DISEASE_CARD_MOBILE_PX_ALLOWED,
  DISEASE_CARD_TYPO_KEYS,
} from "../components/mobile/diseaseCardTypography";
import { MIN_BODY_FONT_PX, MOBILE_TYPO } from "../components/mobile/tokens";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" } }),
}));

import Disclosure, { DiseaseCard } from "./Disclosure";

const ROOT = process.cwd();
const SRC = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");

/** Tailwind 유틸 → px. 프로젝트 재정의 없음(`text-xs`는 tailwindcss 기본 0.75rem). */
const UTIL_PX: Record<string, number> = { "text-xs": 12, "text-sm": 14, "text-base": 16, "text-caption": 12.5 };

/** className 문자열에서 폰트 크기(px)를 뽑는다. 없으면 null(상속). */
function fontPxOf(className: string): number | null {
  const arb = /text-\[(\d+(?:\.\d+)?)px\]/.exec(className);
  if (arb) return Number(arb[1]);
  for (const [util, px] of Object.entries(UTIL_PX)) {
    if (new RegExp(`(^|\\s)${util}(\\s|$)`).test(className)) return px;
  }
  return null;
}

/** 결과 화면 1건 — 카드 안 요소가 최대한 많이 켜지도록 구성한다. */
const FIXTURE = {
  flagged_count: 1,
  total_q_count: 1,
  total_visit_sum: 14,
  total_med_sum: 210,
  standard_reports: {
    "3번 질문: 10년 이내 입원/수술/7회이상통원/30일이상투약": [
      {
        first_date: "2019-03-11",
        latest_date: "2024-08-18",
        first_diagnosis_date: "2019-03-11",
        code: "M51.9",
        display_code: "M51.9",
        name: "상세불명의 만성 폐쇄성 폐질환에 동반된 급성 하기도감염",
        visit: 12,
        med_days: 210,
        med_days_30plus: true,
        inpatient: 14,
        inpatient_count: 2,
        inpatient_periods: [
          { start: "2024-03-11", end: "2024-03-18", days: 8, hospital: "가톨릭대학교 서울성모병원 호흡기내과의원" },
        ],
        surgery_count: 1,
        surgeries: ["2022-08-09 관절경하수술"],
        procedures: ["도수치료"],
        surgery_suspected: ["척추수술 관련 행위"],
        surgery_suspected_grade: "강",
        treatment_ongoing: true,
        treatment_ongoing_reason: "최근 3개월 내 투약 지속",
        insurance_only: true,
        hospitals: ["가톨릭대학교 서울성모병원 호흡기내과의원"],
        first_hospital: "가톨릭대학교 서울성모병원 호흡기내과의원",
        last_hospital: "가톨릭대학교 서울성모병원 호흡기내과의원",
        visit_records: [{ date: "2024-08-18", count: 2, hospital: "가톨릭대학교 서울성모병원 호흡기내과의원" }],
        med_records: [{ date: "2024-08-18", days: 30, hospital: "가톨릭대학교 서울성모병원 호흡기내과의원" }],
        surgery_events: [{ date: "2022-08-09", hospital: "가톨릭대학교 서울성모병원 호흡기내과의원" }],
        detail: "5년 이내 통원 12회, 투약 210일",
      },
    ],
  },
  easy_reports: {},
  all_disease_summary: [],
  standard_kakao: "테스트 카카오 메시지",
  easy_kakao: "",
  parse_errors: [],
  warnings: [],
  meritz_easy_message: "",
};

/** 카드 단독 렌더용 — 페이지 픽스처와 **같은 항목**을 쓴다(두 경로가 갈라지지 않게). */
const CARD_ITEM = FIXTURE.standard_reports[
  "3번 질문: 10년 이내 입원/수술/7회이상통원/30일이상투약"
][0];

beforeEach(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/**
 * ★뷰포트 스텁 — `useIsMobile`은 matchMedia만 본다(CSS 미디어쿼리가 아니다).
 *  ★`vi.stubGlobal`은 jsdom의 `window.matchMedia`를 덮지 못한다(훅이 보는 것은 window 쪽이다) —
 *    실측으로 확인해 182·266 테스트와 같은 `Object.defineProperty(window, ...)` 방식으로 맞췄다.
 *  리스너를 실제로 붙여 **렌더 이후에도 전환**할 수 있게 한다: 업로드 동선은 모바일에서 268a 시트로
 *  갈라지므로, 결과 화면까지는 데스크톱 동선으로 간 뒤 카드만 모바일로 전환해 **같은 결과 데이터**로
 *  두 렌더를 비교한다(데이터가 달라서 생기는 오판을 제거한다).
 */
let vpMobile = false;
const vpListeners = new Set<() => void>();

function setViewport(mobile: boolean) {
  vpMobile = mobile;
  vpListeners.clear();
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      get matches() {
        return vpMobile;
      },
      media: query,
      onchange: null,
      addEventListener: (_: string, cb: () => void) => vpListeners.add(cb),
      removeEventListener: (_: string, cb: () => void) => vpListeners.delete(cb),
      addListener: (cb: () => void) => vpListeners.add(cb),
      removeListener: (cb: () => void) => vpListeners.delete(cb),
      dispatchEvent: () => false,
    }),
  });
}

/** matchMedia 자체를 없앤다(구형 브라우저·SSR 대비 폴백 경로). */
function removeMatchMedia() {
  vpListeners.clear();
  Object.defineProperty(window, "matchMedia", { configurable: true, writable: true, value: undefined });
}

async function renderResult() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      // ★268b 진행 폴링을 먼저 잡는다 — `finished`를 주지 않으면 폴링이 끝나지 않아 테스트가 멈춘다(실측).
      if (url.includes("/api/analyze/progress/")) {
        return new Response(JSON.stringify({ finished: true, items: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/api/analyze")) {
        return new Response(JSON.stringify(FIXTURE), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } });
    }),
  );
  const utils = render(
    <MemoryRouter initialEntries={["/disclosure?mode=agent"]}>
      <Disclosure />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.upload(
    utils.container.querySelector('input[type="file"]') as HTMLInputElement,
    new File(["%PDF-1.4"], "t.pdf", { type: "application/pdf" }),
  );
  for (const box of Array.from(utils.container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]'))) {
    await user.click(box);
  }
  await user.click(screen.getByRole("button", { name: "AI 고지 리스크 점검" }));
  await waitFor(() => expect(screen.getAllByText(/급성 하기도감염/).length).toBeGreaterThan(0));
  return utils;
}

/** 질병 카드(article) 안에서 크기가 지정된 요소를 전부 모은다. */
function cardFontSizes(container: HTMLElement): { px: number; text: string }[] {
  const card = Array.from(container.querySelectorAll("article")).find((el) =>
    el.textContent?.includes("급성 하기도감염"),
  );
  expect(card, "질병 카드가 렌더되지 않았다(빈 화면 오통과 방지)").toBeTruthy();
  expect(card!.textContent, "판정 상세가 비어 있다(빈 렌더 오통과 방지)").toContain("투약 210일");
  const out: { px: number; text: string }[] = [];
  for (const el of Array.from(card!.querySelectorAll<HTMLElement>("*"))) {
    const cls = el.className || "";
    // ★공용 `Badge`(Q 번호)는 270 범위 밖이라 제외한다 — 별도 테스트로 무변경을 고정한다.
    if (/(^|\s)text-caption(\s|$)/.test(cls)) continue;
    const px = fontPxOf(cls);
    if (px != null) out.push({ px, text: (el.textContent || "").slice(0, 24) });
  }
  return out;
}

// ── 맵 계약 ────────────────────────────────────────────────────────────────
describe("폰트 맵 계약", () => {
  it("★모바일 값이 265 하한(15px) 이상이고 토큰(16·15)만 쓴다", () => {
    for (const key of DISEASE_CARD_TYPO_KEYS) {
      const px = fontPxOf(DISEASE_CARD_MOBILE_TYPO[key]);
      expect(px, key).not.toBeNull();
      expect(px!, key).toBeGreaterThanOrEqual(MIN_BODY_FONT_PX);
      expect(DISEASE_CARD_MOBILE_PX_ALLOWED as readonly number[], key).toContain(px!);
    }
    // 265 토큰 정의 자체는 변경 금지 — 적용만 한다.
    expect(MOBILE_TYPO.body.px).toBe(16);
    expect(MOBILE_TYPO.sub.px).toBe(15);
    expect(MIN_BODY_FONT_PX).toBe(15);
  });

  it("★title(20px)은 쓰지 않는다 — 카드가 화면 요약 헤더와 동급이 되면 계층이 뒤집힌다", () => {
    for (const key of DISEASE_CARD_TYPO_KEYS) {
      expect(fontPxOf(DISEASE_CARD_MOBILE_TYPO[key]), key).not.toBe(MOBILE_TYPO.title.px);
    }
  });

  it("★정보 계층 역전 0 — 병명 ≥ 판정 상세 ≥ 그 외", () => {
    const px = (k: (typeof DISEASE_CARD_TYPO_KEYS)[number]) => fontPxOf(DISEASE_CARD_MOBILE_TYPO[k])!;
    expect(px("name")).toBeGreaterThanOrEqual(px("detail"));
    for (const key of DISEASE_CARD_TYPO_KEYS) {
      if (key === "name" || key === "detail") continue;
      expect(px("detail"), key).toBeGreaterThanOrEqual(px(key));
      expect(px("name"), key).toBeGreaterThanOrEqual(px(key));
    }
  });

  it("★데스크톱 맵이 HEAD 원문 값 그대로다(A안 미채택의 실증)", () => {
    // 소스에 리터럴로 남아 있어야 한다 — 하나라도 바뀌면 데스크톱 화면이 변한 것이다.
    const desktop = /const DISEASE_CARD_DESKTOP_TYPO[^{]*\{([\s\S]*?)\n\};/.exec(SRC);
    expect(desktop).toBeTruthy();
    const body = desktop![1];
    for (const [key, cls] of Object.entries({
      name: "text-[15px]",
      code: "text-[11px]",
      insuranceOnly: "text-[11px]",
      meta: "text-xs",
      detail: "text-[13px]",
      chip: "text-xs",
      medToggle: "text-[11px]",
      medNote: "text-[12px]",
      evidenceToggle: "text-[11px]",
      evidenceBody: "text-[11px]",
      evidenceNote: "text-[10px]",
      suspectNote: "text-[11px]",
      bottom: "text-xs",
    })) {
      expect(body, key).toContain(`${key}: "${cls}"`);
    }
  });

  it("두 맵의 키 집합이 같다(한쪽만 바뀌는 것을 막는다)", () => {
    expect(Object.keys(DISEASE_CARD_MOBILE_TYPO).sort()).toEqual([...DISEASE_CARD_TYPO_KEYS].sort());
    const desktop = /const DISEASE_CARD_DESKTOP_TYPO[^{]*\{([\s\S]*?)\n\};/.exec(SRC)![1];
    for (const key of DISEASE_CARD_TYPO_KEYS) expect(desktop, key).toContain(`${key}: "`);
  });
});

// ── 분기 방식 ──────────────────────────────────────────────────────────────
describe("★분기 방식 — CSS가 아니라 JS 판정", () => {
  it("`useIsMobile`로 갈리고 CSS 숨김·미디어쿼리 분기가 없다", () => {
    expect(SRC).toContain("const fz = isMobile ? DISEASE_CARD_MOBILE_TYPO : DISEASE_CARD_DESKTOP_TYPO;");
    const cardStart = SRC.indexOf("function DiseaseCard(");
    const cardEnd = SRC.indexOf("function DisclosureSection(");
    const card = SRC.slice(cardStart, cardEnd);
    // 카드 안에 md:/sm: 폰트 분기나 hidden 토글이 들어오지 않았다.
    expect(card).not.toMatch(/(sm|md|lg):text-\[/);
    expect(card).not.toMatch(/(md:hidden|hidden md:|@media)/);
  });

  it("Chip 기본 크기가 현행(text-xs)이라 미지정 호출부는 데스크톱 그대로다", () => {
    expect(SRC).toContain('sizeCls = "text-xs"');
  });
});

// ── 실렌더 ────────────────────────────────────────────────────────────────
describe("실렌더 — 데스크톱", () => {
  it("★카드 폰트가 HEAD와 같다(10·11·12·12.5·13·15px 구성 유지)", async () => {
    setViewport(false);
    const { container } = await renderResult();
    const sizes = cardFontSizes(container);
    expect(sizes.length).toBeGreaterThan(5);
    // 데스크톱은 15px 미만이 **정상**이다 — 여기서 15px 이상만 나오면 A안이 새어 들어온 것이다.
    expect(sizes.some((s) => s.px < MIN_BODY_FONT_PX)).toBe(true);
    expect(Math.max(...sizes.map((s) => s.px))).toBe(15);
    expect(sizes.some((s) => s.px === 13)).toBe(true); // 판정 상세
    expect(sizes.some((s) => s.px === 11)).toBe(true); // 상병코드·안내
  });

  it("matchMedia가 없는 환경도 데스크톱으로 폴백한다", async () => {
    removeMatchMedia();
    const { container } = await renderResult();
    const sizes = cardFontSizes(container);
    expect(Math.max(...sizes.map((s) => s.px))).toBe(15);
    expect(sizes.some((s) => s.px < MIN_BODY_FONT_PX)).toBe(true);
  });
});

describe("실렌더 — 모바일", () => {
  /**
   * ★페이지 동선을 타지 않고 **카드만** 렌더한다.
   *  이유(실측): 결과 화면을 띄운 뒤 matchMedia를 모바일로 뒤집으면 268a 업로드 시트까지 함께 다시
   *  마운트되면서 `act`가 정착하지 않는다. 데스크톱 페이지 렌더는 위 describe가 이미 덮고 있고,
   *  270이 바꾸는 것은 카드 내부뿐이라 **같은 item으로 두 뷰포트를 대조**하는 편이 표적이 정확하다.
   */
  const renderCard = () => render(<DiseaseCard item={CARD_ITEM} qNum="Q3" />);

  it("★카드 안 폰트 지정이 전부 15px 이상이다", () => {
    setViewport(true);
    const { container } = renderCard();
    const sizes = cardFontSizes(container);
    expect(sizes.length).toBeGreaterThan(5);
    expect(sizes.filter((s) => s.px < MIN_BODY_FONT_PX)).toEqual([]);
  });

  it("병명 16 · 판정 상세 16 · 상병코드 15 — 실제 요소로 확인", () => {
    setViewport(true);
    const { container } = renderCard();
    const card = container.querySelector("article")!;
    const find = (text: string) =>
      Array.from(card.querySelectorAll<HTMLElement>("*")).find((el) => el.textContent?.trim() === text);
    expect(fontPxOf(find(CARD_ITEM.name)!.className), "병명").toBe(16);
    expect(fontPxOf(find("M51.9")!.className), "상병코드").toBe(15);
    // 판정 상세는 `displayJudgmentDetail`이 문장을 다듬으므로 문자열이 아니라 역할로 찾는다.
    const detail = card.querySelector<HTMLElement>("div.font-medium.leading-relaxed")!;
    expect(detail, "판정 상세 줄").toBeTruthy();
    expect(detail.textContent, "판정 상세가 비어 있다").toContain("투약");
    expect(fontPxOf(detail.className), "판정 상세").toBe(16);
  });

  it("★Q 배지는 손대지 않았다(공용 Badge · 267 동결분)", () => {
    setViewport(true);
    const { container } = renderCard();
    const badge = Array.from(container.querySelectorAll<HTMLElement>("span")).find((el) =>
      el.className.includes("text-caption"),
    );
    expect(badge, "Q 배지가 text-caption을 유지한다").toBeTruthy();
    expect(badge!.className).not.toMatch(/text-\[\d+px\]/); // 크기 덮어쓰기 없음
  });

  it("★같은 카드를 데스크톱으로 렌더하면 폰트가 원래대로 돌아온다(오버라이드가 모바일 한정)", () => {
    setViewport(true);
    const mobile = cardFontSizes(renderCard().container).map((s) => s.px);
    cleanup();
    setViewport(false);
    const desktop = cardFontSizes(renderCard().container).map((s) => s.px);
    expect(mobile.length).toBe(desktop.length); // 요소 수 동일 — 마크업은 그대로다
    expect(Math.min(...desktop)).toBeLessThan(MIN_BODY_FONT_PX);
    expect(Math.min(...mobile)).toBeGreaterThanOrEqual(MIN_BODY_FONT_PX);
    // 크기를 키운 것이지 줄인 곳은 없다.
    expect(mobile.every((px, i) => px >= desktop[i])).toBe(true);
  });

  it("matchMedia가 없으면 카드도 데스크톱 폰트로 폴백한다", () => {
    removeMatchMedia();
    const { container } = renderCard();
    const sizes = cardFontSizes(container).map((s) => s.px);
    expect(Math.max(...sizes)).toBe(15);
    expect(Math.min(...sizes)).toBeLessThan(MIN_BODY_FONT_PX);
  });
});

// ── 보호 영역 ──────────────────────────────────────────────────────────────
describe("보호 영역", () => {
  it("★265 하한 가드·토큰 정의는 변경하지 않는다(적용만)", () => {
    const guard = readFileSync(resolve(ROOT, "src/components/mobile/mobileTokens.test.ts"), "utf8");
    expect(guard).toContain("★모바일 컴포넌트에 15px 미만 폰트 지정이 없다");
    expect(guard).toContain("expect(offenders).toEqual([]);");
    const tokens = readFileSync(resolve(ROOT, "src/components/mobile/tokens.ts"), "utf8");
    expect(tokens).toContain("export const MIN_BODY_FONT_PX = 15;");
  });

  it("★183 산식 문구·투약 배지 색 규칙 무변경", () => {
    expect(SRC).toContain("label={<>투약 <AnimatedNumber value={item.med_days ?? 0} />일</>}");
    expect(SRC).toContain('(item.med_days ?? 0) >= 30 ? "amber" : (item.med_days ?? 0) > 0 ? "emerald" : "gray"');
    expect(SRC).toContain("{MED_SUM_FORMULA_NOTE}");
  });

  it("★Q1~Q5 판정·기간 라벨 무변경(267 동결분)", () => {
    expect(SRC).toContain('{ Q1: "3개월 이내", Q2: "10년 이내", Q3: "5년 이내" }');
    expect(SRC).toContain('{ Q1: "3개월 이내", Q2: "1년 이내", Q3: "5년 이내", Q4: "5년 초과 10년 이내", Q5: "5년 이내" }');
  });

  it("★모바일 클래스가 Tailwind 생성 대상임이 보장된다(조용한 무효화 방지)", () => {
    // 위험: 임의값 유틸은 소스 스캔으로만 생성된다. 정본이 `.ts` 파일이라 스캔 여부가 환경에 달리면
    //   오버라이드가 **조용히 무효**가 될 수 있다(로컬은 248 껍데기 빌드라 CSS로 확인 불가).
    //   → 같은 클래스가 이미 `.tsx`에서 쓰이고 있는지를 고정해 어느 경로로든 생성되게 한다.
    const tsx = readdirSync(resolve(ROOT, "src/components/mobile"))
      .filter((f) => f.endsWith(".tsx") && !f.includes(".test."))
      .map((f) => readFileSync(resolve(ROOT, "src/components/mobile", f), "utf8"))
      .join("\n");
    for (const cls of new Set(Object.values(DISEASE_CARD_MOBILE_TYPO))) {
      expect(tsx, `${cls}가 .tsx에서도 쓰여야 생성이 보장된다`).toContain(cls);
    }
  });

  it("★모바일 정본 파일은 크기만 다룬다(색·굵기·간격에 손대지 않는다)", () => {
    const mobile = readFileSync(resolve(ROOT, "src/components/mobile/diseaseCardTypography.ts"), "utf8");
    const code = mobile.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
    expect(code).not.toMatch(/font-(bold|semibold|medium)|text-(ink|amber|sky|accent|rose|emerald)|px-|py-|mb-/);
  });
});
