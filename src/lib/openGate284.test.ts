/// <reference types="node" />
// BOHUMFIT-284 — 오픈 게이트 마감이 프런트에 남긴 표면.
//
//   ★고정하는 계약
//     ①429가 사전에 있다 — 284가 limiter를 4종에 추가해 실제로 늘어난다.
//       (그전에는 규칙이 없어 서버가 정확히 알려준 사유가 폴백으로 뭉개졌다)
//     ②업로드 상한(쪽수·압축 해제) 문구가 행동 지침형으로 매핑된다
//     ③백엔드 문구와 프런트 규칙이 어긋나지 않는다 — 언어 경계라 상수를 공유할 수 없어
//       183·276a·277b 선례대로 **교차 테스트**로 묶는다
//     ④새 문구도 271 위생(PII·기술 용어 0)을 지킨다
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { allUserMessages, FALLBACK_ERROR_MESSAGE, looksTechnical, toUserErrorMessage } from "./errorMessages";

const ROOT = process.cwd();
const MAIN_PY = readFileSync(resolve(ROOT, "backend/main.py"), "utf-8");
const GUARD_PY = readFileSync(resolve(ROOT, "backend/pdf_guard.py"), "utf-8");

/** 백엔드가 실제로 내보내는 429 문구(`_rate_limit_handler`). */
const SERVER_429 = "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.";

describe("★429 — 284가 채운 공백", () => {
  it("서버 문구가 폴백으로 뭉개지지 않는다", () => {
    const message = toUserErrorMessage(SERVER_429);
    expect(message).not.toBe(FALLBACK_ERROR_MESSAGE);
  });

  it("얼마나 기다릴지를 알려준다 — '잠시 후'만으로는 행동이 안 정해진다", () => {
    expect(toUserErrorMessage(SERVER_429)).toContain("1분");
  });

  it("백엔드 문구가 바뀌면 이 테스트가 먼저 깨진다", () => {
    expect(MAIN_PY).toContain(SERVER_429);
  });
});

describe("★업로드 상한(F-7) 문구", () => {
  it.each([
    ["PDF 쪽수가 너무 많아요(1,000쪽 초과). 발급 기간을 나눠 받은 뒤 다시 올려 주세요.", "쪽수가 너무 많아요"],
    ["PDF 내용이 지나치게 커서 열지 못했어요. 발급 기간을 나눠 받은 뒤 다시 올려 주세요.", "열지 못했어요"],
  ])("%s → 다음 행동을 알려준다", (detail, expected) => {
    const message = toUserErrorMessage(detail);
    expect(message).toContain(expected);
    expect(message).toContain("발급 기간을 나눠");
    expect(message).not.toBe(FALLBACK_ERROR_MESSAGE);
  });

  it("백엔드 상한 문구와 프런트 규칙이 같은 조각을 쓴다", () => {
    // `pdf_guard.py`가 문구를 바꾸면 사전이 못 잡게 되므로 조각 단위로 묶는다.
    expect(GUARD_PY).toContain("쪽수가 너무 많아요");
    expect(GUARD_PY).toContain("내용이 지나치게 커서");
    expect(GUARD_PY).toContain("발급 기간을 나눠 받은 뒤 다시 올려 주세요");
  });

  it("★크기(MB) 문구와 뒤섞이지 않는다 — 순서 의존이 생기면 조용히 오매핑된다", () => {
    expect(toUserErrorMessage("개별 PDF 크기는 15MB를 넘을 수 없습니다.")).toContain("파일 용량이 너무 커요");
    expect(toUserErrorMessage("전체 PDF 합계 크기는 40MB를 넘을 수 없습니다.")).toContain("파일 수를 줄이거나");
  });
});

describe("★새 문구도 271 위생을 지킨다", () => {
  it("PII·기술 용어가 없다", () => {
    for (const message of allUserMessages()) {
      expect(looksTechnical(message)).toBe(false);
      expect(message).not.toMatch(/\.pdf|\.xlsx|서류 \d/);
    }
  });

  it("모든 문구가 다음 행동을 담는다", () => {
    for (const message of allUserMessages()) {
      expect(message).toMatch(/주세요|확인해|다시 시도/);
    }
  });
});
