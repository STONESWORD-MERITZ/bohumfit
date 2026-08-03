/// <reference types="node" />
// BOHUMFIT-183 — 화면 투약 배지 산식 표기(표시 전용).
//   ★핵심 가드: ①배지 라벨·값·색이 그대로일 것 ②설명은 기본 접힘·펼치면 확정 문구 그대로
//   ③30일 임계 색 전환 지점 무변경 ④문구가 백엔드 상수와 같을 것.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MED_SUM_FORMULA_NOTE } from "../lib/disclosureWindow";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" } }),
}));

import Disclosure from "./Disclosure";

const ROOT = process.cwd();

/** 투약 N일짜리 결과 1건. 색 전환(30일) 경계를 파라미터로 바꾼다. */
function fixtureWithMedDays(medDays: number) {
  return {
    flagged_count: 1,
    total_q_count: 1,
    total_visit_sum: 14,
    total_med_sum: medDays,
    standard_reports: {
      "3번 질문: 10년 이내 입원/수술/7회이상통원/30일이상투약": [
        {
          first_date: "2022-08-09",
          latest_date: "2025-07-22",
          first_diagnosis_date: "2022-08-09",
          code: "I10",
          display_code: "I10",
          name: "고혈압",
          visit: 14,
          med_days: medDays,
          med_days_30plus: medDays >= 30,
          inpatient: 0,
          inpatient_count: 0,
          inpatient_periods: [],
          surgery_count: 0,
          surgeries: [],
          procedures: [],
          surgery_suspected: [],
          treatment_ongoing: null,
          hospitals: ["가보자의원"],
          first_hospital: "가보자의원",
          last_hospital: "가보자의원",
          detail: `투약 ${medDays}일`,
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
}

beforeEach(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderWithResult(medDays: number) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/analyze")) {
        return new Response(JSON.stringify(fixtureWithMedDays(medDays)), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
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
  await waitFor(() => expect(screen.getAllByText(/고혈압/).length).toBeGreaterThan(0));
  return utils;
}

describe("★배지 자체는 그대로다", () => {
  it("라벨이 HEAD와 같고 교체되지 않았다", async () => {
    const { container } = await renderWithResult(1002);
    // "투약 {N}일" 라벨 — ★"처방일수 합계" 등으로 교체하지 않았다.
    expect(container.textContent).toContain("투약");
    expect(container.textContent).not.toContain("처방일수 합계");
    // ※값 자체는 `AnimatedNumber` 카운트업이라 렌더 직후 최종값이 아니다 —
    //   값 표시는 소스에서 기존 바인딩이 유지됐는지로 확인한다(아래 색 규칙 테스트와 같은 방식).
    const src = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    expect(src).toContain("label={<>투약 <AnimatedNumber value={item.med_days ?? 0} />일</>}");
  });

  it("★30일 임계 색 전환 지점이 그대로다(29 → emerald / 30 → amber)", async () => {
    const src = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    // 색 규칙 조건식이 HEAD와 동일한 형태로 남아 있는지(임계값·분기 순서 포함).
    expect(src).toContain('(item.med_days ?? 0) >= 30 ? "amber" : (item.med_days ?? 0) > 0 ? "emerald" : "gray"');
  });
});

describe("산식 설명 — 기본 접힘 · 접이식(모바일 포함 동일 동작)", () => {
  it("처음에는 설명이 보이지 않는다", async () => {
    await renderWithResult(1002);
    expect(screen.queryByTestId("med-formula-note")).toBeNull();
    expect(screen.getAllByTestId("med-formula-toggle").length).toBeGreaterThan(0);
  });

  it("토글을 누르면 확정 문구가 그대로 나온다", async () => {
    await renderWithResult(1002);
    const toggle = screen.getAllByTestId("med-formula-toggle")[0];
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(toggle);
    expect(screen.getByTestId("med-formula-note").textContent).toBe(MED_SUM_FORMULA_NOTE);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");

    fireEvent.click(toggle);
    expect(screen.queryByTestId("med-formula-note")).toBeNull();
  });

  it("★설명 줄에 폭 고정이 없다(모바일에서 잘리지 않는다)", async () => {
    await renderWithResult(1002);
    fireEvent.click(screen.getAllByTestId("med-formula-toggle")[0]);
    const note = screen.getByTestId("med-formula-note");
    expect(note.className).not.toMatch(/min-w-\[|w-\[\d+px\]|whitespace-nowrap/);
    expect(note.className).toContain("break-keep");
  });

  it("★토글 노출 조건이 투약 배지와 완전히 같다(`metric.med`)", () => {
    // 실측: `metric.med`는 med_days 값이 아니라 **질문별 표시 규칙**(`getMetricVisibility`)으로 정해진다.
    //   그래서 med_days=0이어도 Q3에서는 배지와 토글이 함께 보이는 것이 정상이다.
    //   두 조건이 갈라지지 않도록 **같은 플래그를 쓰는지**를 소스로 고정한다.
    const src = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    const badgeAt = src.indexOf("label={<>투약 <AnimatedNumber");
    const toggleAt = src.indexOf('data-testid="med-formula-toggle"');
    expect(badgeAt).toBeGreaterThan(-1);
    expect(toggleAt).toBeGreaterThan(badgeAt);
    // 배지와 토글 사이 구간에 다른 게이트가 끼어들지 않고 같은 `metric.med`로 열린다.
    expect(src.slice(badgeAt, toggleAt)).toContain("{metric.med && (");
    expect(src).toContain("{metric.med && medFormulaOpen && (");
  });
});

describe("★문구 단일 출처", () => {
  it("백엔드 `report_pdf.py` 상수와 문자열이 완전히 같다", () => {
    const py = readFileSync(resolve(ROOT, "backend/pipeline/report_pdf.py"), "utf8");
    const m = /MED_SUM_FORMULA_NOTE = "([^"]+)"/.exec(py);
    expect(m).toBeTruthy();
    expect(m?.[1]).toBe(MED_SUM_FORMULA_NOTE);
  });

  it("확정 문구 그대로다(임의 변경 금지)", () => {
    expect(MED_SUM_FORMULA_NOTE).toBe("동일 날짜에 여러 처방이 있으면 가장 긴 처방일수 1건만 반영한 합계입니다.");
  });
});
