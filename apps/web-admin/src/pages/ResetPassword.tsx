import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Lock, ArrowLeft, CheckCircle2, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { apiUrl } from '../config/runtime';

export const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      setError('Mã token khôi phục không tồn tại hoặc đã bị thiếu trên đường dẫn.');
      return;
    }

    if (password.length < 6) {
      setError('Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/reset-password'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đặt lại mật khẩu thất bại. Mã token có thể đã hết hạn.');
      }

      setSuccess(true);
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4 font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
        <div className="text-center mb-6">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 items-center justify-center mb-4">
            <Lock className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Đặt Lại Mật Khẩu</h1>
          <p className="text-sm text-slate-400 mt-1">
            Thiết lập mật khẩu mới cho tài khoản của bạn.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium flex items-start space-x-2">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success ? (
          <div className="space-y-6 text-center">
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex flex-col items-center space-y-2">
              <CheckCircle2 className="w-8 h-8 shrink-0" />
              <p className="font-semibold text-white">Thành công!</p>
              <p className="text-slate-300 text-xs">
                Mật khẩu của bạn đã được thay đổi. Đang chuyển hướng sang trang đăng nhập...
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleReset} className="space-y-4">
            {!token && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-xs">
                Cảnh báo: Không tìm thấy mã token hợp lệ trên URL. Vui lòng bấm vào liên kết trong email gửi lại.
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Mật khẩu mới
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Ít nhất 6 ký tự"
                  className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Xác nhận mật khẩu mới
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Nhập lại mật khẩu mới"
                className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !token}
              className="w-full mt-2 py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 text-sm"
            >
              {loading ? 'Đang cập nhật...' : 'Xác Nhận Đổi Mật Khẩu'}
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
