// BOHUMFIT-248 P1: 빌드 산출물 스모크 게이트 — "조용한 껍데기 번들"(247 실측: 앱 코드 없는
// 343 kB 산출물이 exit 0으로 통과) 재발을 차단한다. `npm run build` 후 실행.
//
// 판정 3종(하나라도 실패 시 exit 1):
//   ① 번들 크기 하한 — 프로덕션 참조치 786,541 B(2026-07-26 실측)의 -20%인 600,000 B 이상
//   ② 필수 앱 문자열 존재 — 화면 고유 문구가 번들에 포함(원문 또는 \uXXXX 이스케이프)
//   ③ index.html 참조 무결 — 참조된 자산 파일이 실제로 존재
//
// ※ 로컬 Windows에서는 Application Control 정책이 신규 네이티브 바이너리(rolldown·oxide)를
//   차단해 정상 번들 생성이 불가하다(248 P1 실측) — 이 게이트는 로컬에서 "껍데기"를 정직하게
//   FAIL로 보고하며, 정상 판정은 정책 예외 적용 후 로컬 또는 CI/Linux 환경에서 수행한다.
import fs from "node:fs";
import path from "node:path";

const DIST = path.resolve(process.cwd(), "dist");
const ASSETS = path.join(DIST, "assets");
const SIZE_FLOOR = 600_000; // 프로덕션 786,541 B 기준 -20% 여유
const REQUIRED_STRINGS = [
  "전후 비교 계산", // 236 화면 고정 문구
  "신규 설계 반영 대상", // 247 신담보 배지
  "가입특약", // 246 신 대분류
];

const failures = [];

if (!fs.existsSync(ASSETS)) {
  failures.push(`dist/assets 부재 — 빌드를 먼저 실행하세요 (${ASSETS})`);
} else {
  const jsFiles = fs.readdirSync(ASSETS).filter((name) => name.endsWith(".js"));
  if (jsFiles.length === 0) failures.push("dist/assets에 JS 번들이 없습니다.");
  const totalJs = jsFiles.reduce((sum, name) => sum + fs.statSync(path.join(ASSETS, name)).size, 0);
  console.log(`JS 번들 ${jsFiles.length}개 · 총 ${totalJs.toLocaleString()} B (하한 ${SIZE_FLOOR.toLocaleString()} B)`);
  if (totalJs < SIZE_FLOOR) failures.push(`① 크기 하한 미달: ${totalJs.toLocaleString()} B < ${SIZE_FLOOR.toLocaleString()} B — 껍데기 번들 의심`);

  const BS = String.fromCharCode(92);
  const escapeUnicode = (text) =>
    Array.from(text)
      .map((ch) => (ch.charCodeAt(0) > 127 ? BS + "u" + ch.charCodeAt(0).toString(16).padStart(4, "0") : ch))
      .join("");
  const bundleText = jsFiles.map((name) => fs.readFileSync(path.join(ASSETS, name), "utf8")).join("\n");
  for (const needle of REQUIRED_STRINGS) {
    const found = bundleText.includes(needle) || bundleText.includes(escapeUnicode(needle));
    console.log(`문자열 "${needle}": ${found ? "OK" : "누락"}`);
    if (!found) failures.push(`② 필수 앱 문자열 누락: "${needle}" — 앱 코드 미포함 의심`);
  }

  const indexHtml = path.join(DIST, "index.html");
  if (!fs.existsSync(indexHtml)) {
    failures.push("③ dist/index.html 부재");
  } else {
    const html = fs.readFileSync(indexHtml, "utf8");
    const refs = [...html.matchAll(/(?:src|href)="\/(assets\/[^"]+)"/g)].map((match) => match[1]);
    for (const ref of refs) {
      if (!fs.existsSync(path.join(DIST, ref))) failures.push(`③ index.html 참조 자산 부재: ${ref}`);
    }
    console.log(`index.html 자산 참조 ${refs.length}건 검사 완료`);
  }
}

if (failures.length > 0) {
  console.error("\n★build:verify 실패 — 산출물을 신뢰할 수 없습니다:");
  for (const failure of failures) console.error(" -", failure);
  process.exit(1);
}
console.log("\nbuild:verify 통과 — 산출물 스모크 3종 정상.");
