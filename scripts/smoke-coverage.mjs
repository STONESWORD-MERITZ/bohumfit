#!/usr/bin/env node
/**
 * BOHUMFIT-262 P5 — 스모크 정본 세트 자동 대조.
 *
 * 255-P2가 `.agent-harness/verify.md`에 고정한 기준 수치를 실 PDF로 재현해 대조한다.
 * 248 `build:verify` 선례를 따라 **불일치는 exit 1로 정직하게 실패**시킨다.
 *
 * 실행: `npm run smoke:coverage`
 *  - 실 PDF가 없으면 경고 후 **skip(exit 0)** — CI·타 환경에서 깨지지 않게 한다(PII로 커밋 불가).
 *  - 파이썬 하위 프로세스로 사용자 동선(엔드포인트 경유)과 동일한 산출을 만들어 비교한다.
 */
import { execFileSync } from "node:child_process";
import { existsSync, globSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const ROOT = resolve(import.meta.dirname, "..");
const PDF_DIR = join(ROOT, "보장분석", "비교분석표");

/** verify.md "스모크 정본 세트" 기준값(BOHUMFIT-301 Human Q6 승인 · 갱신 시 verify.md와 함께 수정). */
const BASELINE = [
  {
    label: "표준(계약별 매트릭스)",
    file: globSync("*-INPUT.pdf", { cwd: PDF_DIR })[0] ?? "__missing-standard.pdf",
    contracts: 15,
    coverageRows: 59,
    enrolled: 29,
    total: 614_860_000,
    monthly: 681_312,
    monthlyActive: 531_312,
    overviewRows: 0,
    warnings: 0,
  },
  {
    label: "overview(합계-only · 239 fallback)",
    file: globSync("*INPUT.pdf", { cwd: PDF_DIR }).find((name) => !name.endsWith("-INPUT.pdf")) ?? "__missing-overview.pdf",
    contracts: 15,
    coverageRows: 58,
    enrolled: 41,
    total: 1_467_790_000,
    monthly: 4_675_189,
    monthlyActive: 4_675_189,
    overviewRows: 25,
    warnings: 2,
    // 256~258 귀속 완결 — overview 담보 26종 전부 회사별 귀속(회사합=합계).
    overviewTotal: 1_358_940_000,
    attributionRate: 99.3,
  },
];

const TODAY = "2026-07-29"; // verify.md 기준일(고정 — 값이 날짜에 의존하지 않도록)

const present = BASELINE.filter((c) => existsSync(join(PDF_DIR, c.file)));
if (present.length === 0) {
  console.warn("[smoke] 실 PDF 정본 세트가 없어 건너뜁니다(로컬 전용 · PII로 커밋 불가).");
  console.warn(`[smoke] 기대 위치: ${PDF_DIR}`);
  console.warn("[smoke] 재확보 절차는 .agent-harness/verify.md 「스모크 정본 세트」 참조.");
  process.exit(0);
}

const PY = `
import io, json, sys
sys.path.insert(0, sys.argv[1])
import openpyxl
from coverage.aggregator import aggregate_coverage_values, build_before, build_final
from coverage.compare import build_after_analysis
from coverage.export_excel import DATA_ROW0, build_workbook_bytes, track_row_of
from coverage.constants import KB_COVERAGES_V2
from coverage.parser import parse_document

pdf_path, today = sys.argv[2], sys.argv[3]
raw = parse_document(open(pdf_path, "rb").read())
before = build_before(raw, today=today)
final = build_final(before, raw.get("diagnosis") or {})
analysis = {"before": before, "final": final, "warnings": raw.get("warnings") or []}
result = build_after_analysis(analysis, {"existing": [], "proposals": []})
after_before = result["after"]["before"]

enrolled = [c for c in before["coverages"] if c.get("enrolled")]
ov = [c for c in enrolled if c.get("overview")]
ids = {str(c["idx"]) for c in before["contract_list"]}

# 회사합 = 합계 대사(귀속된 행 전수)
mismatch = 0
for row in enrolled:
    by = {k: v for k, v in (row.get("by_company") or {}).items() if v is not None}
    if not by:
        continue
    if aggregate_coverage_values(by, row.get("agg")) != row.get("summary"):
        mismatch += 1

attributed = [c for c in ov if any(v is not None for v in (c.get("by_company") or {}).values())]
ov_total = sum(c["summary"] or 0 for c in ov)
rate = round(sum(c["summary"] or 0 for c in attributed) / ov_total * 100, 1) if ov_total else None

# 엑셀도 사용자 동선과 동일하게 생성해 시트2 회사합=합계를 재대조
# BOHUMFIT-291(S3): 49행 양식 — 시트 '컨설팅 전', 담보 7행~, 합계 F·G(2열), 회사당 2열(H~).
wb = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(result)))
ws = wb["컨설팅 전"]
n = len(before["contract_list"]) if (not ov or attributed) else 0
xl_mismatch = 0
def _num(v):
    return v if isinstance(v, (int, float)) else 0
if n:
    # BOHUMFIT-292(S4·Phase F): 종수술 위 2열 헤더 행이 들어가 좌표는 track_row_of()로(값·기준값 무변경).
    for spec in KB_COVERAGES_V2:
        r = track_row_of(spec.row_id)
        cells = [_num(ws.cell(row=r, column=8 + 2 * i).value) + _num(ws.cell(row=r, column=9 + 2 * i).value) for i in range(n)]
        total = _num(ws.cell(row=r, column=6).value) + _num(ws.cell(row=r, column=7).value)
        if sum(cells) != total:
            xl_mismatch += 1

# 해지 0 → 전=후 동일
after_rows = {c["kb_name"]: c.get("summary") for c in after_before["coverages"]}
same_after = sum(1 for c in before["coverages"] if after_rows.get(c["kb_name"]) != c.get("summary"))

print(json.dumps({
    "contracts": len(before["contract_list"]),
    "coverageRows": len(before["coverages"]),
    "enrolled": len(enrolled),
    "total": sum(c["summary"] or 0 for c in enrolled),
    "monthly": before["premium"]["monthly_total"],
    "monthlyActive": before["premium"].get("monthly_total_active"),
    "overviewRows": len(ov),
    "warnings": len(raw.get("warnings") or []),
    "overviewTotal": ov_total,
    "attributionRate": rate,
    "companySumMismatch": mismatch,
    "excelCompanySumMismatch": xl_mismatch,
    "beforeAfterDiff": same_after,
    "unknownKeys": sum(1 for c in enrolled
                       if any(k not in ids and v is not None
                              for k, v in (c.get("by_company") or {}).items())),
    "sheets": wb.sheetnames,
}, ensure_ascii=False))
`;

const tmp = mkdtempSync(join(tmpdir(), "bohumfit-smoke-"));
const script = join(tmp, "probe.py");
writeFileSync(script, PY, "utf8");

let failures = 0;
try {
  for (const expected of present) {
    const out = execFileSync(
      "python",
      [script, join(ROOT, "backend"), join(PDF_DIR, expected.file), TODAY],
      { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
    );
    const actual = JSON.parse(out.trim().split("\n").pop());
    const problems = [];

    for (const key of ["contracts", "coverageRows", "enrolled", "total", "monthly",
                       "monthlyActive", "overviewRows", "warnings", "overviewTotal",
                       "attributionRate"]) {
      if (expected[key] === undefined) continue;
      if (actual[key] !== expected[key]) {
        problems.push(`${key}: 기준 ${expected[key]} vs 실측 ${actual[key]}`);
      }
    }
    // 기준표와 무관하게 항상 성립해야 하는 불변식(246/253/259 계약).
    if (actual.companySumMismatch !== 0) problems.push(`회사합≠합계 ${actual.companySumMismatch}건(payload)`);
    if (actual.excelCompanySumMismatch !== 0) problems.push(`회사합≠합계 ${actual.excelCompanySumMismatch}건(엑셀 시트2)`);
    if (actual.beforeAfterDiff !== 0) problems.push(`해지 0인데 전≠후 ${actual.beforeAfterDiff}건`);
    if (actual.unknownKeys !== 0) problems.push(`계약 미확인('?') 잔존 ${actual.unknownKeys}건`);
    const sheets = ["표지(세로)", "컨설팅 전", "컨설팅 후", "최종"];  // BOHUMFIT-291 4시트
    if (JSON.stringify(actual.sheets) !== JSON.stringify(sheets)) {
      problems.push(`시트 구성 ${JSON.stringify(actual.sheets)}`);
    }

    if (problems.length) {
      failures += 1;
      console.error(`✗ ${expected.label}`);
      for (const p of problems) console.error(`    - ${p}`);
    } else {
      console.log(`✓ ${expected.label} — 계약 ${actual.contracts} · 총액 ${actual.total.toLocaleString()} · `
        + `월납 ${actual.monthly.toLocaleString()} · 회사합=합계 0 · 전=후 0`);
    }
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}

const skipped = BASELINE.length - present.length;
if (skipped) console.warn(`[smoke] ${skipped}건은 파일 부재로 건너뜀.`);

if (failures) {
  console.error(`\n[smoke] ★${failures}건 불일치 — 기준값(.agent-harness/verify.md)과 산출이 어긋났습니다.`);
  process.exit(1);
}
console.log(`\n[smoke] 정본 세트 ${present.length}건 전부 기준값 일치.`);
