/// <reference types="node" />
// BOHUMFIT-277(B-F5) — 콘솔·Sentry로 나가는 문자열의 PII 제거.
//
//   ★275 실측: 271은 **화면**만 막았고, 미매핑 원문은 `console.warn`에 그대로 남아
//     Sentry breadcrumb·exception으로 실려 나갈 수 있었다. `beforeSend`는 request data/cookies만 지웠다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FALLBACK_ERROR_MESSAGE, sanitizeParseErrors, scrubPii, toUserErrorMessage } from "./errorMessages";

const ROOT = process.cwd();
const REAL = "가상고객A 최근 3개월.pdf";

afterEach(() => vi.restoreAllMocks());

describe("scrubPii", () => {
  it("★`{이모지} {파일명}: {사유}` 접두를 통째로 지운다(한글 파일명은 공백 포함)", () => {
    const out = scrubPii(`🔒 ${REAL}: 비밀번호가 필요합니다.`);
    expect(out).not.toContain("가상고객A");
    expect(out).not.toContain(".pdf");
    // ★사유는 남는다 — 개발자가 디버깅할 수 있어야 한다.
    expect(out).toContain("비밀번호");
  });

  it("문장 중간의 파일명 토큰·엑셀 확장자도 지운다", () => {
    expect(scrubPii("업로드 실패: report_2026.pdf 손상")).not.toContain(".pdf");
    expect(scrubPii("내보내기 실패 result.xlsx")).not.toContain(".xlsx");
  });

  it("멱등이다 — 이미 정규화된 문구는 그대로", () => {
    const already = "서류 1: 비밀번호가 필요합니다.";
    expect(scrubPii(already)).toBe(already);
  });

  it("빈 입력에서 던지지 않는다", () => {
    expect(scrubPii("")).toBe("");
  });
});

describe("★미매핑 오류 콘솔 경로", () => {
  it("console.warn에 원본 파일명이 남지 않는다", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const message = toUserErrorMessage(new Error(`🔒 ${REAL}: 알 수 없는 사유 zzz`));
    // 화면 문구는 여전히 폴백(271 계약 유지)
    expect(message).toBe(FALLBACK_ERROR_MESSAGE);
    const logged = warn.mock.calls.flat().join(" ");
    expect(logged).not.toContain("가상고객A");
    expect(logged).not.toContain(".pdf");
  });
});

describe("★271 방어 2선이 살아 있다", () => {
  it("서버가 이미 slot으로 준 문구도 화면에서 깨지지 않는다(멱등)", () => {
    const out = sanitizeParseErrors(["서류 1: 비밀번호가 필요합니다."]);
    expect(out.length).toBe(1);
    expect(out[0]).toContain("서류 1");
  });

  it("★서버 정규화가 실패해도 화면에는 파일명이 나가지 않는다(2선 유지)", () => {
    const out = sanitizeParseErrors([`🔒 ${REAL}: 비밀번호가 필요합니다.`]);
    expect(out.join(" ")).not.toContain("가상고객A");
    expect(out.join(" ")).toContain("서류 1");
  });

  it("`sanitizeParseErrors` 함수가 제거되지 않았다(271 계약)", () => {
    const src = readFileSync(resolve(ROOT, "src/lib/errorMessages.ts"), "utf8");
    expect(src).toContain("export function sanitizeParseErrors");
    const page = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    expect(page).toContain("sanitizeParseErrors(");
  });
});

describe("★Sentry beforeSend 확장", () => {
  const main = readFileSync(resolve(ROOT, "src/main.tsx"), "utf8");

  it("breadcrumb·exception·message를 모두 scrub한다", () => {
    expect(main).toContain("event.breadcrumbs");
    expect(main).toContain("event.exception?.values");
    expect(main).toContain("scrubPii(event.message)");
  });

  it("기존 request data/cookies 삭제는 유지된다", () => {
    expect(main).toContain("delete event.request.data");
    expect(main).toContain("delete event.request.cookies");
  });
});
