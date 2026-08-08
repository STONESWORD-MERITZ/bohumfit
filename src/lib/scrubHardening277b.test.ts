/// <reference types="node" />
// BOHUMFIT-277b — 277 반려 보정(R1 scrub 대상 확장 · 프런트/백엔드 동일 규칙).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { REDACTED, safeErrorSummary, scrubPii, toUserErrorMessage } from "./errorMessages";

const ROOT = process.cwd();
const MIXED = "가상고객A 최근 3개월.pdf I10 고혈압 서울병원 M51.9 강남한의원";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); });

describe("★R1 — 건강정보 scrub", () => {
  it("상병코드를 지운다(ICD-10 형식)", () => {
    for (const code of ["I10", "M51.9", "S83.2", "C00"]) {
      expect(scrubPii(`진단 ${code} 확인`)).not.toContain(code);
    }
  });

  it("의료기관명을 지운다", () => {
    for (const org of ["서울병원", "강남한의원", "행복의원", "튼튼클리닉", "중앙보건소"]) {
      expect(scrubPii(`${org} 방문`)).not.toContain(org);
      expect(scrubPii(`${org} 방문`)).toContain(REDACTED);
    }
  });

  it("★과잉 scrub 금지 — 사유 문구·버전은 남는다", () => {
    const keep = "PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.";
    expect(scrubPii(keep)).toBe(keep);
    expect(scrubPii("상품 2607(2.0)")).toContain("2607");
  });
});

describe("★raw 비전송 계약(병명 사전 부재)", () => {
  it("★운영(프로덕션)에서는 원문을 담지 않는다", () => {
    // Sentry는 프로덕션에서만 켜진다 → 그 환경의 동작을 고정한다.
    vi.stubEnv("DEV", false);
    const s = JSON.stringify(safeErrorSummary(new Error(MIXED)));
    for (const secret of ["가상고객A", "I10", "고혈압", "서울병원", ".pdf"]) {
      expect(s).not.toContain(secret);
    }
    expect(s).toContain("Error");   // 진단 정보(kind)는 남는다
    expect(s).toContain("length");
    expect(s).not.toContain("preview");
  });

  it("개발 환경에서만 scrub한 미리보기를 남긴다(디버깅 가능성 유지)", () => {
    vi.stubEnv("DEV", true);
    const s = JSON.stringify(safeErrorSummary(new Error(MIXED)));
    expect(s).toContain("preview");
    // ★미리보기도 scrub은 통과한다 — 상병코드·기관명은 여기서도 지워진다.
    expect(s).not.toContain("I10");
    expect(s).not.toContain("서울병원");
  });

  it("★미매핑 오류 console에 원문·건강정보가 남지 않는다(운영)", () => {
    vi.stubEnv("DEV", false);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    toUserErrorMessage(new Error(MIXED));
    const logged = JSON.stringify(warn.mock.calls);
    for (const secret of ["가상고객A", "I10", "고혈압", "서울병원"]) {
      expect(logged).not.toContain(secret);
    }
  });
});

describe("★프런트·백엔드 동일 규칙(교차 테스트)", () => {
  // 183·276a 선례: 언어 경계라 상수를 공유할 수 없으므로 **규칙 문자열을 교차 단언**한다.
  const py = readFileSync(resolve(ROOT, "backend/pii.py"), "utf8");

  it("ICD 패턴이 같다", () => {
    const pattern = String.raw`[A-Z]\d{2}(?:\.\d{1,2})?`;
    expect(py).toContain(pattern);
    const ts = readFileSync(resolve(ROOT, "src/lib/errorMessages.ts"), "utf8");
    expect(ts).toContain(pattern);
  });

  it("기관명 접미사 목록이 같다", () => {
    const suffixes = ["병원", "의원", "한의원", "클리닉", "보건소", "의료원", "치과", "약국"];
    const ts = readFileSync(resolve(ROOT, "src/lib/errorMessages.ts"), "utf8");
    for (const s of suffixes) {
      expect(py).toContain(s);
      expect(ts).toContain(s);
    }
  });

  it("치환 라벨이 같다", () => {
    expect(py).toContain('REDACTED = "[제거됨]"');
    expect(REDACTED).toBe("[제거됨]");
  });
});

describe("Sentry beforeSend 배선 유지", () => {
  const main = readFileSync(resolve(ROOT, "src/main.tsx"), "utf8");
  it("message·breadcrumb·exception 모두 scrub한다", () => {
    expect(main).toContain("event.breadcrumbs");
    expect(main).toContain("event.exception?.values");
    expect(main).toContain("scrubPii(event.message)");
  });
});
