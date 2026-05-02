import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      navigate("/");
    }
  };

  const handleKakao = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
  };

  return (
    <div className="min-h-screen bg-[#F8F9FC] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* 로고 */}
        <div className="text-center mb-10">
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">
            SUR<span className="text-[#4F46E5]">IT</span>
          </h1>
          <p className="text-sm text-gray-400 mt-2">설계사 전용 AI 플랫폼</p>
        </div>

        {/* 카카오 로그인 */}
        <button
          onClick={handleKakao}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-colors"
          style={{ background: "#FEE500", color: "#191919" }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M9 1C4.58 1 1 3.8 1 7.24c0 2.22 1.48 4.17 3.7 5.27l-.94 3.47c-.08.3.26.54.52.36L8.05 13.7c.31.03.63.05.95.05 4.42 0 8-2.8 8-6.24S13.42 1 9 1Z"
              fill="#191919"
            />
          </svg>
          카카오로 시작하기
        </button>

        {/* 구분선 */}
        <div className="flex items-center gap-3 my-6">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-gray-300 font-semibold">또는</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* 이메일 로그인 */}
        <form onSubmit={handleEmail} className="space-y-3">
          <input
            type="email"
            placeholder="이메일"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full bg-white rounded-xl px-4 py-3 text-sm text-gray-800 placeholder:text-gray-300 shadow-[0_1px_3px_rgba(0,0,0,0.06)] focus:ring-2 focus:ring-[#4F46E5]/30 focus:outline-none"
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full bg-white rounded-xl px-4 py-3 text-sm text-gray-800 placeholder:text-gray-300 shadow-[0_1px_3px_rgba(0,0,0,0.06)] focus:ring-2 focus:ring-[#4F46E5]/30 focus:outline-none"
          />

          {error && (
            <p className="text-xs text-red-500 font-semibold">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-[#4F46E5] hover:bg-[#4338CA] disabled:opacity-50 text-white font-bold rounded-xl text-sm transition-colors shadow-[0_2px_8px_rgba(79,70,229,0.3)]"
          >
            {loading ? "로그인 중..." : "이메일로 로그인"}
          </button>
        </form>

        {/* 회원가입 링크 */}
        <p className="text-center text-xs text-gray-400 mt-6">
          아직 계정이 없으신가요?{" "}
          <a href="/signup" className="text-[#4F46E5] font-bold hover:underline">
            회원가입
          </a>
        </p>
      </div>
    </div>
  );
}
