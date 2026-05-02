import { useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "../lib/supabase";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
    } else {
      setDone(true);
    }
  };

  if (done) {
    return (
      <div className="min-h-screen bg-[#F8F9FC] flex items-center justify-center px-4">
        <div className="w-full max-w-sm text-center">
          <div className="text-4xl mb-4">📧</div>
          <h2 className="text-lg font-extrabold text-gray-900 mb-2">이메일을 확인해 주세요</h2>
          <p className="text-sm text-gray-400 mb-6">
            {email}으로 인증 메일을 보냈습니다.
            <br />
            메일의 링크를 클릭하면 가입이 완료됩니다.
          </p>
          <Link
            to="/login"
            className="text-sm font-bold text-[#4F46E5] hover:underline"
          >
            로그인으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FC] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">
            SUR<span className="text-[#4F46E5]">IT</span>
          </h1>
          <p className="text-sm text-gray-400 mt-2">회원가입</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
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
            placeholder="비밀번호 (6자 이상)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full bg-white rounded-xl px-4 py-3 text-sm text-gray-800 placeholder:text-gray-300 shadow-[0_1px_3px_rgba(0,0,0,0.06)] focus:ring-2 focus:ring-[#4F46E5]/30 focus:outline-none"
          />

          {error && <p className="text-xs text-red-500 font-semibold">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-[#4F46E5] hover:bg-[#4338CA] disabled:opacity-50 text-white font-bold rounded-xl text-sm transition-colors shadow-[0_2px_8px_rgba(79,70,229,0.3)]"
          >
            {loading ? "가입 중..." : "회원가입"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-6">
          이미 계정이 있으신가요?{" "}
          <Link to="/login" className="text-[#4F46E5] font-bold hover:underline">
            로그인
          </Link>
        </p>
      </div>
    </div>
  );
}
