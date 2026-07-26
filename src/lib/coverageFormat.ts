// BOHUMFIT-247: 보장금액 포맷터 단일 소스(페이지·표시 블록 공용 — 237 A 규칙).

export function formatCoverageAmount(value: number | null | undefined): string {
  // BOHUMFIT-237 A: 보장금액 한글 단위 표기("1억 2,000만원" — 백엔드 format_krw와 동일 규칙).
  if (value == null) return "-";
  if (value === 0) return "0원";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  const eok = Math.floor(abs / 100_000_000);
  const man = Math.floor((abs % 100_000_000) / 10_000);
  const won = abs % 10_000;
  const parts: string[] = [];
  if (eok) parts.push(`${eok.toLocaleString("ko-KR")}억`);
  if (man) parts.push(`${man.toLocaleString("ko-KR")}만`);
  if (won || parts.length === 0) parts.push(won.toLocaleString("ko-KR"));
  return `${sign}${parts.join(" ")}원`;
}

export function formatCoverageDeltaAmount(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : "-"}${formatCoverageAmount(Math.abs(value))}`;
}
