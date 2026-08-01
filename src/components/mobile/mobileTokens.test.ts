// BOHUMFIT-265 — P1 토큰 가드.
//   ★15px 미만 회색 본문 금지 / 면 전용 색(라임·그린티) 폰트·보더 금지 / 장식 그라디언트 금지 /
//   터치 규격(56·44)·간격·반경 상수화 — 화면 개편(266~)이 이 규칙을 어기지 못하게 막는다.
import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import {
  MIN_BODY_FONT_PX,
  MOBILE_LAYOUT,
  MOBILE_TOUCH,
  MOBILE_TYPO,
  GRADIENT_ALLOWED,
  SURFACE_ONLY_COLORS,
  DISCLOSURE_BADGES,
  UNDO_TOAST_MS,
  UNDO_TOAST_ALLOWED_SCOPES,
} from "./tokens";

const ROOT = process.cwd();
const CSS = readFileSync(join(ROOT, "src/index.css"), "utf8");

function listFiles(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(join(ROOT, dir))) {
    const rel = `${dir}/${name}`;
    if (statSync(join(ROOT, rel)).isDirectory()) listFiles(rel, out);
    else if (/\.(tsx|ts)$/.test(name) && !/\.test\.tsx?$/.test(name)) out.push(rel);
  }
  return out;
}
const MOBILE_FILES = listFiles("src/components/mobile");
/** 주석을 제거한 실행 코드만 검사한다(설명 문구가 가드를 오탐시키지 않도록). */
const codeOf = (src: string) =>
  src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

describe("BOHUMFIT-265 P1 모바일 토큰", () => {
  it("타이포 3단이 CSS 변수와 TS 상수에 모두 정의된다", () => {
    for (const v of ["--text-m-title", "--text-m-body", "--text-m-sub"]) {
      expect(CSS).toContain(v);
    }
    expect(MOBILE_TYPO.title.px).toBe(20);
    expect(MOBILE_TYPO.body.px).toBe(16);
    expect(MOBILE_TYPO.sub.px).toBe(15);
  });

  it("★본문·보조 하한이 15px 이상이다(회색 본문 축소 금지)", () => {
    expect(MIN_BODY_FONT_PX).toBe(15);
    expect(MOBILE_TYPO.body.px).toBeGreaterThanOrEqual(MIN_BODY_FONT_PX);
    expect(MOBILE_TYPO.sub.px).toBeGreaterThanOrEqual(MIN_BODY_FONT_PX);
  });

  it("★모바일 컴포넌트에 15px 미만 폰트 지정이 없다", () => {
    const offenders: string[] = [];
    for (const file of MOBILE_FILES) {
      const code = codeOf(readFileSync(join(ROOT, file), "utf8"));
      // text-[13px] / fontSize: 13 / font-size: 13px 형태를 모두 잡는다.
      const sizes = [
        ...code.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g),
        ...code.matchAll(/fontSize:\s*(\d+(?:\.\d+)?)/g),
        ...code.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g),
      ].map((m) => Number(m[1]));
      for (const size of sizes) if (size < MIN_BODY_FONT_PX) offenders.push(`${file}:${size}px`);
    }
    expect(offenders).toEqual([]);
  });

  it("터치 규격 — 주요 액션 56 · 탭 영역 44", () => {
    expect(MOBILE_TOUCH.action).toBe(56);
    expect(MOBILE_TOUCH.tap).toBe(44);
    expect(CSS).toContain("--size-m-action");
    expect(CSS).toContain("--size-m-tap");
    // 탭 영역 확장 유틸이 존재하고 레이아웃을 밀지 않는다(absolute + 중앙 정렬).
    expect(CSS).toMatch(/\.m-tap::before[\s\S]{0,240}position: absolute/);
    expect(CSS).toContain("translate(-50%, -50%)");
  });

  it("간격·반경 — 좌우 20 / 카드 20 · 버튼 15 · 배지 8", () => {
    expect(MOBILE_LAYOUT).toEqual({ gutter: 20, radiusCard: 20, radiusBtn: 15, radiusBadge: 8 });
    for (const v of ["--spacing-m-gutter", "--radius-m-card", "--radius-m-btn", "--radius-m-badge"]) {
      expect(CSS).toContain(v);
    }
  });

  it("★면 전용 색(라임·그린티)을 글자·테두리로 쓰지 않는다", () => {
    for (const file of MOBILE_FILES) {
      const code = codeOf(readFileSync(join(ROOT, file), "utf8"));
      for (const hex of SURFACE_ONLY_COLORS) {
        expect(code.includes(`color: "${hex}"`)).toBe(false);
        expect(code.includes(`borderColor: "${hex}"`)).toBe(false);
      }
      expect(code).not.toMatch(/text-lime|border-lime|text-greentea|border-greentea/);
    }
  });

  it("★장식 그라디언트를 쓰지 않는다", () => {
    expect(GRADIENT_ALLOWED).toBe(false);
    for (const file of MOBILE_FILES) {
      const code = codeOf(readFileSync(join(ROOT, file), "utf8"));
      expect(code).not.toMatch(/linear-gradient|radial-gradient|bg-gradient-/);
    }
  });

  it("상태 면(경고·검토·중립)이 신설되고 기존 브랜드 토큰은 그대로다", () => {
    expect(CSS).toContain("--color-surface-warning");
    expect(CSS).toContain("--color-surface-review");
    // 기존 값 무변경(회귀 가드)
    expect(CSS).toContain("--color-accent-600: #084734;");
    expect(CSS).toContain("--color-lime: #CEF17B;");
    expect(CSS).toContain("--color-greentea: #CDEDB3;");
  });

  it("배지 4단 라벨이 Human 확정(10년)과 일치한다", () => {
    expect(DISCLOSURE_BADGES.major10y.label).toBe("고지대상 · 10년");
    expect(DISCLOSURE_BADGES.minor3m.label).toBe("고지대상 · 3개월");
    expect(DISCLOSURE_BADGES.review1y.label).toBe("검토 · 1년 재검사");
    expect(DISCLOSURE_BADGES.none.label).toBe("해당없음");
    // ★5년 표기 잔재 0 — 라벨뿐 아니라 **주석까지** 스캔한다(Codex 반려: 주석 2건이 남아 있었다).
    //   알릴의무 질문 기간(Q3 "5년 이내" 등)·심평원 자료 범위는 별개 도메인이라 모바일 컴포넌트 밖에 있고,
    //   여기서는 배지 정본이 있는 `src/components/mobile` 전체만 검사한다.
    expect(JSON.stringify(DISCLOSURE_BADGES)).not.toContain("5년");
    const offenders = MOBILE_FILES.filter((file) => readFileSync(join(ROOT, file), "utf8").includes("5년"));
    expect(offenders).toEqual([]);
  });

  it("되돌리기 토스트는 6초 · 허용 범위 3곳뿐(남용 금지)", () => {
    expect(UNDO_TOAST_MS).toBe(6000);
    expect([...UNDO_TOAST_ALLOWED_SCOPES]).toEqual(["cancel-confirm", "copy-done", "analysis-done"]);
  });
});
