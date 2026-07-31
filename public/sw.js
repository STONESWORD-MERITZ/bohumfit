/* BOHUMFIT-264 — PWA 앱 셸 서비스워커 (수동 작성).
 *
 * ★vite-plugin-pwa를 쓰지 않는다: 플러그인이 vite 계열 버전 이동을 요구할 수 있고,
 *   241에서 rolldown 네이티브 바인딩 문제로 로컬 빌드가 깨진 전례가 있어 버전 고정이 계약이다.
 *   대신 표준 SW API만 사용한다(빌드 파이프라인 무접촉 — `public/`은 그대로 복사된다).
 *
 * ★캐시 정책(264 범위)
 *   - 캐시함: 앱 셸(내비게이션 문서)·동일 출처 정적 자산(js/css/font/image)·오프라인 폴백.
 *   - ★캐시하지 않음: 분석 결과·업로드 응답·엑셀/PDF 등 파일 응답, 인증 토큰이 붙는 API,
 *     GET 이외 메서드, 교차 출처(백엔드 API 도메인). PII가 디스크에 남지 않게 하는 것이 우선이다.
 *   - 분석 결과 캐시는 **265에서 A안(24h 만료·로그아웃 삭제)** 으로 다룬다.
 *     여기서는 `isCacheableResponse()` 훅만 만들어 두고 실제 캐시는 하지 않는다.
 */

// ★버전을 올리면 구 캐시가 activate에서 삭제된다(stale SW 방지).
const CACHE_VERSION = "bohumfit-shell-v1";
const OFFLINE_URL = "/offline.html";

/** 설치 시 미리 담아둘 최소 자산(해시 파일명은 런타임 캐시로 처리). */
const PRECACHE_URLS = [OFFLINE_URL, "/favicon.svg", "/site.webmanifest"];

/** 캐시 금지 경로 — PII·민감 응답이 디스크에 남지 않게 한다. */
const NEVER_CACHE_PATTERNS = [
  /\/api\//i,
  /\/coverage\//i,
  /\/analyze/i,
  /\/auth\//i,
  /\/rest\/v1\//i, // Supabase
  /\.(?:xlsx|xls|pdf|csv)(?:$|\?)/i,
];

/** 정적 자산 판별(동일 출처 한정). */
function isStaticAsset(url) {
  return /\.(?:js|mjs|css|woff2?|ttf|otf|png|jpg|jpeg|svg|webp|ico)(?:$|\?)/i.test(url.pathname);
}

/** ★캐시 가능 여부 단일 판정 — 265에서 정책을 넓힐 때도 이 함수만 바꾼다. */
function isCacheableRequest(request) {
  if (request.method !== "GET") return false;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return false; // 백엔드 API 등 교차 출처 제외
  if (NEVER_CACHE_PATTERNS.some((re) => re.test(url.pathname))) return false;
  return request.mode === "navigate" || isStaticAsset(url);
}

/** 응답을 캐시에 넣어도 되는지(불투명·오류 응답 제외). */
function isCacheableResponse(response) {
  return !!response && response.status === 200 && response.type === "basic";
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE_URLS)),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith("bohumfit-shell-") && key !== CACHE_VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  // 새 버전 즉시 적용(앱이 사용자 동의를 받은 뒤 보낸다).
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!isCacheableRequest(request)) return; // ★그 외 요청은 SW가 손대지 않는다(원래 동작 그대로)

  // 내비게이션: 네트워크 우선 → 실패 시 캐시 → 그래도 없으면 오프라인 폴백.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (isCacheableResponse(response)) {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          return cached || (await caches.match(OFFLINE_URL)) || Response.error();
        }),
    );
    return;
  }

  // 정적 자산: 캐시 우선 + 백그라운드 갱신(stale-while-revalidate).
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (isCacheableResponse(response)) {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
