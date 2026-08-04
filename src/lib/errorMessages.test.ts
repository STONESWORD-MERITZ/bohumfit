/// <reference types="node" />
// BOHUMFIT-271 — 오류 문구 사전.
//   ★핵심 계약: ①주요 detail이 행동 지침형으로 매핑 ②미매핑은 폴백(원문 미노출)
//   ③문구에 PII·기술 용어·에러 코드 없음 ④XHR·fetch 양 경로가 같은 사전을 쓴다
//   ⑤268b 폴링 실패는 여전히 조용하다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  allUserMessages,
  FALLBACK_ERROR_MESSAGE,
  looksTechnical,
  NETWORK_ERROR_MESSAGE,
  sanitizeParseErrors,
  toUserErrorMessage,
} from "./errorMessages";

const ROOT = process.cwd();

afterEach(() => vi.restoreAllMocks());

describe("주요 detail → 행동 지침형 문구", () => {
  it.each([
    ["PDF 파일만 업로드할 수 있어요.", "심평원·공단에서 받은 PDF인지"],
    ["PDF 형식이 아닌 파일이 포함돼 있습니다. 심평원 진료 PDF만 업로드해 주세요.", "PDF 파일만 올릴 수 있어요"],
    ["PDF는 최대 10개까지 업로드할 수 있습니다.", "나눠서 올려"],
    ["개별 PDF 크기는 15MB를 넘을 수 없습니다.", "발급 기간을 나눠"],
    ["전체 PDF 합계 크기는 40MB를 넘을 수 없습니다.", "파일 수를 줄이거나"],
    ["🔒 문서: 비밀번호가 걸린 PDF입니다. 생년월일을 입력해 주세요.", "생년월일 8자리"],
    ["PDF에서 진료 데이터를 추출하지 못했습니다.", "심평원에서 발급한 진료내역 PDF가 맞는지"],
    ["로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요.", "다시 로그인한 뒤"],
    ["무료 분석 최초 5회를 모두 사용했습니다. 구독 후 계속 이용하세요.", "요금제에서"],
    ["분석이 시간 내에 끝나지 않았어요.", "파일 수를 줄이거나"],
    ["서버에서 분석을 완료하지 못했어요. 잠시 후 다시 시도해 주세요.", "잠시 후 다시"],
    ["파일을 생성하지 못했습니다.", "파일을 만들지 못했어요"],
  ])("%s → 다음 행동을 알려준다", (detail, expected) => {
    const message = toUserErrorMessage(detail);
    expect(message).toContain(expected);
  });

  it("모든 문구가 '무엇을 하면 되는지'를 담는다", () => {
    // 행동을 지시하는 어미가 최소 한 번은 들어간다.
    for (const message of allUserMessages()) {
      expect(message).toMatch(/주세요|확인해|다시 시도/);
    }
  });
});

describe("★미매핑 — 폴백만 나가고 원문은 화면에 없다", () => {
  it("모르는 오류는 폴백 문구가 된다", () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(toUserErrorMessage(new Error("ValueError: unexpected token < in JSON at position 0"))).toBe(
      FALLBACK_ERROR_MESSAGE,
    );
  });

  it("HTML·스택 같은 기술 응답도 그대로 새지 않는다", () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const raw = "<html><body>500 Internal Server Error</body></html>";
    const message = toUserErrorMessage(raw);
    expect(message).toBe(FALLBACK_ERROR_MESSAGE);
    expect(message).not.toContain("html");
    expect(message).not.toContain("500");
  });

  it("빈 오류·null·undefined도 폴백으로 간다", () => {
    expect(toUserErrorMessage("")).toBe(FALLBACK_ERROR_MESSAGE);
    expect(toUserErrorMessage(null)).toBe(FALLBACK_ERROR_MESSAGE);
    expect(toUserErrorMessage(undefined)).toBe(FALLBACK_ERROR_MESSAGE);
  });

  it("★원문은 콘솔에만 남는다(개발 진단용)", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    toUserErrorMessage("알 수 없는 서버 응답 XYZ-500");
    expect(warn).toHaveBeenCalled();
    expect(String(warn.mock.calls[0].join(" "))).toContain("XYZ-500");
  });
});

describe("★문구 위생 — PII·기술 용어 0", () => {
  it("사전의 모든 문구에 기술 흔적이 없다", () => {
    for (const message of allUserMessages()) {
      expect(looksTechnical(message)).toBe(false);
    }
  });

  it("사전의 모든 문구에 파일명·확장자·환자 식별 표현이 없다", () => {
    for (const message of allUserMessages()) {
      expect(message).not.toMatch(/\.pdf|\.xlsx|파일명|환자|고객명|성명/);
    }
  });

  it("★파일명을 넣어도 문구에 반영되지 않는다(PII 유출 차단)", () => {
    const message = toUserErrorMessage("PDF 파일만 업로드할 수 있어요. (김OO 진료내역.pdf)");
    expect(message).not.toContain("김OO");
    expect(message).not.toContain(".pdf");
  });

  it("네트워크 문구는 다음 행동을 준다", () => {
    expect(toUserErrorMessage(new TypeError("Failed to fetch"))).toBe(NETWORK_ERROR_MESSAGE);
    expect(NETWORK_ERROR_MESSAGE).toContain("연결을 확인");
  });
});

describe("★parse_errors 살균 — 파일명(환자명)이 화면에 오르지 않는다", () => {
  // ★실측 문구: 실 PDF(비밀번호 걸린 파일)로 `parse_single_pdf`를 돌려 그대로 얻은 값이다.
  const REAL = "🔒 정홍규 최근 3개월.pdf: PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.";

  it("환자명이 든 파일명이 제거되고 서류 번호로 대체된다", () => {
    const [line] = sanitizeParseErrors([REAL]);
    expect(line).not.toContain("정홍규");
    expect(line).not.toContain(".pdf");
    expect(line).toContain("서류 1");
    // 사유는 행동 지침형으로 바뀐다.
    expect(line).toContain("생년월일 8자리를 입력한 뒤");
  });

  it("여러 서류가 같은 사유면 번호를 합쳐 한 줄로 만든다", () => {
    const lines = sanitizeParseErrors([REAL, "🔒 김OO 진료.pdf: PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요."]);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain("서류 1·2");
    expect(lines[0]).not.toMatch(/정홍규|김OO/);
  });

  it("다른 사유는 줄을 나눈다", () => {
    const lines = sanitizeParseErrors([
      REAL,
      "⚠️ 환자명 포함.pdf: PDF에서 진료 데이터를 추출하지 못했습니다.",
    ]);
    expect(lines).toHaveLength(2);
    expect(lines.join(" ")).not.toMatch(/정홍규|환자명 포함|\.pdf/);
  });

  it("빈 배열·빈 문자열을 안전하게 처리한다", () => {
    expect(sanitizeParseErrors([])).toEqual([]);
    expect(sanitizeParseErrors(["", "   "])).toEqual([]);
  });

  it("파일명 패턴이 아닌 문구도 사전을 통과해 원문이 새지 않는다", () => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
    const [line] = sanitizeParseErrors(["Traceback (most recent call last): KeyError 'x'"]);
    expect(line).toContain(FALLBACK_ERROR_MESSAGE);
    expect(line).not.toContain("Traceback");
  });

  it("화면이 원본 배열이 아니라 살균 결과를 렌더한다", () => {
    const disclosure = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    expect(disclosure).toContain("sanitizeParseErrors(result.parse_errors || [])");
    // 원본을 그대로 map 하던 자리가 남아 있지 않다.
    expect(disclosure).not.toContain("{(result.parse_errors || []).map(");
  });
});

describe("★적용 지점 — 화면이 원문을 뿌리지 않는다", () => {
  const disclosure = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
  const coverage = readFileSync(resolve(ROOT, "src/pages/CoverageRemodel.tsx"), "utf8");

  it("고지 화면이 사전을 쓰고 파일명을 문구에 넣지 않는다", () => {
    expect(disclosure).toContain("toUserErrorMessage");
    // 파일명 삽입(PII)이 사라졌다.
    expect(disclosure).not.toContain("${nonPdf.name}");
    expect(disclosure).not.toContain("${tooLarge.name}");
  });

  it("보장분석 화면도 같은 사전을 쓴다(XHR·fetch 양 경로 통일)", () => {
    expect(coverage).toContain("toUserErrorMessage(uploadError)");
    expect(coverage).toContain("toUserErrorMessage(exportError)");
    // 원문을 그대로 넣던 자리가 남아 있지 않다.
    expect(coverage).not.toContain("uploadError.message");
    expect(coverage).not.toContain("exportError.message");
  });

  it("고지 화면도 원문 message를 화면에 넣지 않는다", () => {
    expect(disclosure).not.toContain('setError(e instanceof Error ? e.message');
  });

  it("★268b 폴링 실패는 여전히 조용하다(오류 문구 미표시)", () => {
    const polling = readFileSync(resolve(ROOT, "src/lib/analysisProgress.ts"), "utf8");
    // 폴링 모듈은 사전을 쓰지 않는다 — 실패해도 화면에 아무것도 띄우지 않는 것이 정답이다.
    expect(polling).not.toContain("toUserErrorMessage");
    expect(polling).not.toContain("setError");
  });

  it("268a `uploadWithProgress`의 detail 규약은 그대로다(구조 무변경)", () => {
    const upload = readFileSync(resolve(ROOT, "src/lib/uploadWithProgress.ts"), "utf8");
    expect(upload).toContain("payload.detail");
    expect(upload).toContain("class UploadError");
    // 사전은 표시 직전 호출부에서만 쓴다 — 전송 계층은 건드리지 않았다.
    expect(upload).not.toContain("toUserErrorMessage");
  });
});
