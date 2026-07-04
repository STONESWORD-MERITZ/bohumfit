// BOHUMFIT-165: 404 Not Found — 브랜드 토큰(ink/accent/canvas/line) 사용, Layout 내부 렌더.
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="mx-auto flex max-w-xl flex-col items-center px-5 py-24 text-center">
      <p className="text-xs font-bold uppercase tracking-[0.25em] text-accent-600">404</p>
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink-900">
        페이지를 찾을 수 없습니다
      </h1>
      <p className="mt-3 text-body leading-7 text-ink-soft break-keep">
        요청하신 주소가 변경되었거나 존재하지 않습니다. 주소를 다시 확인해 주세요.
      </p>
      <Link
        to="/"
        className="mt-8 rounded-btn bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-700"
      >
        홈으로 돌아가기
      </Link>
    </section>
  );
}
