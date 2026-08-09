/// <reference types="node" />
// BOHUMFIT-279 — 265 오프라인 캐시 A안 철회 · 고지 문구를 실동작에 정합.
//
//   ★275 B-F4: `saveAnalysis`/`listAnalyses`/`getAnalysis` 호출부가 제품 코드에 **0건**인데
//     방침·동의문은 "최근 5건 24시간 임시 보관"을 단정했고, 실제 `sessionStorage` 보관은 문구에 없었다.
//     → 고지와 실동작이 **양방향으로** 어긋나 있었다. 이 파일이 그 정합을 고정한다.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { SESSION_RESULT_TTL_MS } from "./sessionResultQueue";

const ROOT = process.cwd();
const read = (p: string) => readFileSync(resolve(ROOT, p), "utf8");
/** 주석 제거 — 변경 사유를 적은 주석이 가드를 오탐시키지 않도록(265 선례). */
const codeOf = (p: string) =>
  read(p).replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

const POLICY = "src/pages/PrivacyPolicy.tsx";
const CONSENT = "src/components/ConsentGate.tsx";

describe("★A안 문구 제거", () => {
  it("사용자 노출 문구에 '5건'·'24시간' 임시 보관 표현이 없다", () => {
    for (const file of [POLICY, CONSENT]) {
      const code = codeOf(file);
      expect(code).not.toContain("최근 5건");
      expect(code).not.toContain("24시간 임시 보관");
      expect(code).not.toContain("오프라인 열람");
    }
  });
});

describe("★기재 항목이 실제 저장물과 일치한다", () => {
  it("기기 임시 보관은 실제 TTL(10분)과 같은 값으로 기재한다", () => {
    expect(SESSION_RESULT_TTL_MS).toBe(10 * 60 * 1000);
    expect(codeOf(POLICY)).toContain("10분");
    expect(codeOf(CONSENT)).toContain("10분");
  });

  it("삭제 조건(로그아웃·계정 전환)이 277 계약과 같게 기재된다", () => {
    expect(codeOf(POLICY)).toContain("로그아웃");
    expect(codeOf(POLICY)).toContain("다른 계정");
    expect(codeOf(CONSENT)).toContain("계정 전환");
  });

  it("서버 보관 기간(90일·7일)은 기존 기재 그대로다", () => {
    for (const file of [POLICY, CONSENT]) {
      expect(codeOf(file)).toContain("90일");
      expect(codeOf(file)).toContain("7일");
    }
    // 서버 상수와 대조(문구가 서버보다 넓거나 좁으면 안 된다).
    const main = read("backend/main.py");
    expect(main).toContain("HISTORY_RETENTION_DAYS = 90");
    expect(main).toContain("HISTORY_RECENT_RETENTION_DAYS = 7");
  });

  it("업로드 원본 미저장 문구는 유지된다", () => {
    expect(codeOf(POLICY)).toContain("업로드 PDF");
    expect(codeOf(CONSENT)).toContain("자료 원본은 분석 후 저장하지 않습니다");
  });
});

describe("★미사용 코드 처리", () => {
  it("`analysisCache`의 저장·조회 API는 제품 코드에서 호출되지 않는다", () => {
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(join(ROOT, dir))) {
        const rel = `${dir}/${name}`;
        if (statSync(join(ROOT, rel)).isDirectory()) walk(rel);
        else if (/\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) && !rel.endsWith("analysisCache.ts"))
          files.push(rel);
      }
    };
    walk("src");
    const offenders = files.filter((f) => /\b(saveAnalysis|listAnalyses|getAnalysis)\s*\(/.test(read(f)));
    expect(offenders).toEqual([]);
  });

  it("★파일은 남기되 미사용·재개 조건이 명시돼 있다", () => {
    const cache = read("src/lib/analysisCache.ts");
    expect(cache).toContain("BOHUMFIT-279");
    expect(cache).toContain("철회");
    expect(cache).toContain("재개 조건");
  });

  it("★277 sessionStorage 삭제 계약과 265 IndexedDB 삭제가 **둘 다** 유지된다", () => {
    const auth = read("src/lib/AuthContext.tsx");
    expect(auth).toContain("clearAnalysisCache()");
    expect(auth).toContain("clearSessionResult()");
  });
});
