// BOHUMFIT-271 — 오류 문구 표준화(262 D-13 ①).
//
//   ★목표: 사용자가 **무엇을 하면 되는지** 알게 한다. 원인만 알려주고 끝내지 않는다.
//   ★원칙
//     · 원인 + 다음 행동을 함께 준다
//     · 기술 용어·에러 코드·스택을 노출하지 않는다
//     · **PII 금지** — 파일명·환자명을 문구에 넣지 않는다(268b 익명화 기조)
//     · 사용자를 탓하지 않는다. 담담하게, 짧게, 존댓말
//   ★미매핑은 **폴백 문구**로 보내고 원문은 화면에 내보내지 않는다.
//     다만 개발 진단이 막히면 곤란하므로 원문은 `console.warn`으로만 남긴다(사용자에게는 보이지 않는다).
//
//   ※268a `uploadWithProgress`의 `detail` 규약(응답 `detail` → `UploadError.message`, `status` 보존)은
//     그대로 두고, **표시 직전에만** 이 사전을 통과시킨다. 402 판정은 `status`로 하므로 159 업셀 동선도 유지된다.
//   ※268b 폴링 실패는 **조용한 폴백**이 정답이라 여기서 다루지 않는다(분석은 계속 진행 중이다).

/** 어떤 오류든 마지막에 걸리는 문구. 원인을 모를 때도 다음 행동은 준다. */
export const FALLBACK_ERROR_MESSAGE = "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.";

/** 네트워크가 끊겼을 때(연결 자체가 실패). */
export const NETWORK_ERROR_MESSAGE =
  "네트워크에 연결하지 못했어요. Wi-Fi 또는 데이터 연결을 확인하고 다시 시도해 주세요.";

type Rule = {
  /** 서버 `detail`이나 오류 메시지에 이 조각이 있으면 매칭(백엔드가 숫자를 채워 보내므로 부분 일치로 잡는다). */
  match: string[];
  message: string;
};

/**
 * 사전 — 위에서부터 먼저 맞는 규칙을 쓴다.
 *   ★자주 나는 것(파일 형식·개수·크기·비밀번호·파싱 실패)을 앞에 둔다.
 */
const RULES: Rule[] = [
  // ── 업로드 전 단계: 파일 자체 문제 ─────────────────────────────────────
  {
    match: ["PDF 파일만", "PDF 형식이 아닌", "PDF만 업로드"],
    message: "PDF 파일만 올릴 수 있어요. 심평원·공단에서 받은 PDF인지 확인해 주세요.",
  },
  {
    match: ["최대", "개까지 업로드"],
    message: "한 번에 올릴 수 있는 개수를 넘었어요. 파일을 나눠서 올려 주세요.",
  },
  // ★"전체 합계"를 "개별 크기"보다 먼저 본다 — 두 문구가 "크기는 …을 넘을 수 없습니다"를 공유해서,
  //   순서를 바꾸면 합계 초과가 개별 크기 문구로 잘못 잡힌다(실측으로 확인).
  {
    match: ["전체 PDF 합계", "합계 크기"],
    message: "전체 용량이 너무 커요. 파일 수를 줄이거나 기간을 나눠 올려 주세요.",
  },
  {
    match: ["개별 PDF 크기", "크기는", "MB를 넘을 수 없습니다"],
    message: "파일 용량이 너무 커요. 발급 기간을 나눠 받은 뒤 다시 올려 주세요.",
  },
  {
    match: ["1개 이상 업로드", "PDF 파일을 업로드"],
    message: "먼저 PDF를 선택해 주세요.",
  },
  // ── 비밀번호·파싱 ────────────────────────────────────────────────────
  {
    match: ["비밀번호", "암호"],
    message: "비밀번호가 걸린 PDF예요. 생년월일 8자리를 입력한 뒤 다시 시도해 주세요.",
  },
  {
    match: ["진료 데이터를 추출하지 못했", "데이터를 추출하지 못"],
    message:
      "PDF에서 진료 내역을 읽지 못했어요. 심평원에서 발급한 진료내역 PDF가 맞는지 확인해 주세요.",
  },
  // ── 동의·권한 ────────────────────────────────────────────────────────
  {
    match: ["동의가 필요", "동의 항목"],
    message: "민감정보 처리 동의가 필요해요. 동의 항목을 확인해 주세요.",
  },
  {
    match: ["정보주체 동의", "업로드 권한"],
    message: "고객 동의 확보 여부를 확인해 주세요.",
  },
  // ── 인증 ─────────────────────────────────────────────────────────────
  {
    match: ["로그인이 필요", "로그인 확인에 실패", "인증"],
    message: "로그인이 풀렸어요. 다시 로그인한 뒤 시도해 주세요.",
  },
  // ── 사용량 ───────────────────────────────────────────────────────────
  {
    match: ["무료 분석", "모두 사용", "한도"],
    message: "이번 달 분석 횟수를 다 썼어요. 요금제에서 이용 계획을 확인해 주세요.",
  },
  // ── 서버·시간 초과 ───────────────────────────────────────────────────
  {
    match: ["시간 내에 끝나지", "시간이 초과", "timeout"],
    message: "분석이 예상보다 오래 걸렸어요. 파일 수를 줄이거나 잠시 후 다시 시도해 주세요.",
  },
  {
    match: ["서버에서 분석을 완료하지", "서버 오류", "일시적인 문제"],
    message: "서버에서 처리하지 못했어요. 잠시 후 다시 시도해 주세요.",
  },
  // ── 파일 생성(엑셀·PDF 내보내기) ─────────────────────────────────────
  {
    match: ["파일을 생성하지", "PDF 생성", "리포트를 생성하지"],
    message: "파일을 만들지 못했어요. 잠시 후 다시 시도해 주세요.",
  },
  // ── 네트워크 ─────────────────────────────────────────────────────────
  {
    match: ["네트워크", "연결하지 못", "Failed to fetch", "NetworkError"],
    message: NETWORK_ERROR_MESSAGE,
  },
];

/** 화면에 내보내면 안 되는 흔적(기술 누출 방지용 자체 점검). */
const TECHNICAL_HINTS = ["Error:", "TypeError", "status", "stack", "<html", "Traceback", "500", "undefined"];

function rawTextOf(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object" && "message" in error) return String((error as { message: unknown }).message);
  return "";
}

/**
 * 오류를 사용자 문구로 바꾼다.
 *   ★어떤 입력이 와도 **사전에 있는 문구 아니면 폴백**만 돌려준다 — 원문이 화면에 새지 않는다.
 */
/**
 * BOHUMFIT-277(B-F5) — 로그·Sentry로 나갈 문자열에서 PII를 지운다.
 *
 *   ★271은 **화면**만 막았다. 콘솔 원문은 Sentry breadcrumb·exception으로 전송될 수 있어
 *   같은 규칙을 여기에도 적용한다(서버 `pii.py`의 최후 방어선과 같은 형태).
 *   ★파일명은 `서류`로 접되 사유 문구는 남긴다 — 개발자가 디버깅할 수 있어야 한다.
 */
export const REDACTED = "[제거됨]";

/** 상병코드 — ICD-10 형식(영문 1자 + 숫자 2자 + 선택 소수점). 백엔드 `pii.py`와 같은 규칙. */
const ICD_RE = /(?<![A-Za-z0-9])[A-Z]\d{2}(?:\.\d{1,2})?(?![A-Za-z0-9])/g;
/** 의료기관명 — 접미사 기반. 백엔드 `pii.py`와 같은 목록. */
const ORG_RE = /[가-힣A-Za-z0-9]*(?:병원|의원|한의원|클리닉|보건소|의료원|치과|약국)/g;

export function scrubPii(text: string): string {
  return String(text ?? "")
    // `{이모지} {파일명}.pdf: {사유}` 접두 구간 — 한글 파일명은 공백을 포함한다.
    .replace(/^\s*\S*\s*[^:]*\.pdf\s*:\s*/i, "서류: ")
    // 문장 중간에 박힌 파일명 토큰.
    .replace(/[^\s:/\\"']*\.(pdf|xlsx|xls)/gi, "서류")
    // ★BOHUMFIT-277b(R1): 상병코드·기관명은 **건강정보 그 자체**라 파일명보다 민감하다.
    .replace(ICD_RE, REDACTED)
    .replace(ORG_RE, REDACTED);
}

/**
 * ★BOHUMFIT-277b(R1) — **raw 본문 비전송 계약**.
 *
 *   병명(진단명)은 **사전이 없어 패턴으로 식별할 수 없다**(`keywords.json` 전수 확인: 상병코드 목록과
 *   수술·검사 키워드만 있고 병명 사전은 없다). 정규식 scrub만으로 "안전하다"고 주장할 수 없으므로,
 *   운영 환경에서는 **원문을 아예 내보내지 않고** 안전한 구조화 필드만 남긴다.
 *   ★개발 환경에서는 scrub한 원문을 함께 남겨 디버깅 가능성을 지킨다(Sentry는 프로덕션에서만 켜진다).
 */
export function safeErrorSummary(error: unknown): Record<string, unknown> {
  const raw = rawTextOf(error);
  const kind = error instanceof Error ? error.name : typeof error;
  const summary: Record<string, unknown> = { kind, length: raw.length };
  if (typeof import.meta !== "undefined" && import.meta.env?.DEV) summary.preview = scrubPii(raw);
  return summary;
}

export function toUserErrorMessage(error: unknown): string {
  const raw = rawTextOf(error).trim();
  if (!raw) return FALLBACK_ERROR_MESSAGE;

  for (const rule of RULES) {
    if (rule.match.some((needle) => raw.includes(needle))) return rule.message;
  }

  // 매칭 실패 — 화면에는 폴백만, 원문은 개발자 콘솔에만 남긴다.
  //   ★BOHUMFIT-277(B-F5): 콘솔 출력도 breadcrumb로 Sentry에 실려 나갈 수 있어 **PII를 지우고** 남긴다.
  //   ★BOHUMFIT-277b(R1): scrub한 원문도 **병명은 남는다**(사전 부재). 운영에서는 원문을 내보내지 않고
  //     `kind`·`length`만 남긴다 — 콘솔은 Sentry breadcrumb로 자동 수집되기 때문이다.
  if (typeof console !== "undefined" && typeof console.warn === "function") {
    console.warn("[BOHUMFIT-271] 매핑되지 않은 오류:", safeErrorSummary(error));
  }
  return FALLBACK_ERROR_MESSAGE;
}

/**
 * BOHUMFIT-271(보정): 서버 `parse_errors`를 화면에 올리기 전에 **파일명을 지운다**.
 *
 *   실측 결과 `pdf_parser`가 만드는 문구는 `🔒 {파일명}: {사유}` 꼴이고, 그 파일명에는
 *   **환자 실명이 들어갈 수 있다**(합성 예: "가상고객A 최근 3개월.pdf"). 이 배열은 결과 화면에서 그대로 렌더되므로
 *   `setError` 경로만 막아서는 PII가 계속 샌다.
 *
 *   ★파일명은 지우되 **몇 번째 서류인지는 남긴다** — 어느 파일을 다시 받아야 하는지 알아야
 *   사용자가 행동할 수 있다(268b가 진행 티커에서 "서류 N"으로 익명화한 것과 같은 방식).
 *   사유 문구는 사전을 통과시켜 행동 지침형으로 바꾸고, 같은 사유가 여러 파일에서 나면 합친다.
 */
export function sanitizeParseErrors(errors: readonly string[]): string[] {
  const seen = new Map<string, number[]>();

  errors.forEach((raw, index) => {
    const text = String(raw || "").trim();
    if (!text) return;
    // `🔒 파일명.pdf: 사유` / `⚠️ 파일명.pdf: 사유` — 앞의 파일명 구간만 떼어낸다.
    const reason = text.replace(/^\s*\S*\s*[^:]*\.pdf\s*:\s*/i, "").trim() || text;
    const message = toUserErrorMessage(reason);
    const slots = seen.get(message) ?? [];
    slots.push(index + 1); // 1-based "서류 N"
    seen.set(message, slots);
  });

  return [...seen.entries()].map(([message, slots]) =>
    slots.length === 1 ? `서류 ${slots[0]}: ${message}` : `서류 ${slots.join("·")}: ${message}`,
  );
}

/** 문구에 기술 흔적이 섞이지 않았는지 확인(테스트·개발 점검용). */
export function looksTechnical(message: string): boolean {
  return TECHNICAL_HINTS.some((hint) => message.includes(hint));
}

/** 사전이 실제로 내보내는 문구 전체(테스트가 PII·기술 용어를 전수 검사한다). */
export function allUserMessages(): string[] {
  return [...RULES.map((r) => r.message), FALLBACK_ERROR_MESSAGE, NETWORK_ERROR_MESSAGE];
}
