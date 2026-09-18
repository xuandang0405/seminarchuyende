import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { KeyRound, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react';
import { apiUrl } from '../config/runtime';

export const ForgotPassword: React.FC = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/forgot-password'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      if (!res.ok) {
        throw new Error('Không thể gửi yêu cầu đặt lại mật khẩu.');
      }

      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Lỗi hệ thống khi gửi yêu cầu.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4 font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
        <div className="text-center mb-6">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 items-center justify-center mb-4">
            <KeyRound className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Quên Mật Khẩu</h1>
          <p className="text-sm text-slate-400 mt-1">
            Nhập email tài khoản để nhận liên kết khôi phục mật khẩu.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium flex items-start space-x-2">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div className="space-y-6 text-center">
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm leading-relaxed flex flex-col items-center space-y-2">
              <CheckCircle2 className="w-8 h-8 shrink-0" />
              <p className="font-semibold text-white">Yêu cầu đã được ghi nhận</p>
              <p className="text-slate-300 text-xs">
                Nếu email này tồn tại trong hệ thống và có hỗ trợ mật khẩu, hướng dẫn đặt lại mật khẩu đã được xử lý.
                (Lưu ý: Tài khoản đăng nhập qua Google vui lòng sử dụng nút Google để truy cập).
              </p>
            </div>
            <Link
              to="/login"
              className="inline-flex items-center space-x-2 text-sm text-indigo-400 hover:text-indigo-300 font-medium"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Quay lại trang Đăng nhập</span>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Email tài khoản
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@tourvoice.vn"
                className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 text-sm"
            >
              {loading ? 'Đang gửi...' : 'Gửi Yêu Cầu Khôi Phục'}
            </button>

            <div className="text-center pt-4">
              <Link
                to="/login"
                className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-white font-medium transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Quay lại trang Đăng nhập</span>
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
