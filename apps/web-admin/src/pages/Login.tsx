import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  Compass, 
  Sparkles, 
  ShieldCheck, 
  ArrowRight, 
  CheckCircle2, 
  Eye, 
  EyeOff, 
  AlertCircle,
  Mail,
  Lock,
  User,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';

export const Login: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loginWithData, logout } = useAuth();

  // If already logged in:
  useEffect(() => {
    if (user) {
      if (user.role === 'user') {
        navigate('/client', { replace: true });
      } else if (user.role === 'admin' || user.role === 'super_admin' || user.role === 'poi_owner') {
        navigate('/', { replace: true });
      }
    }
  }, [user, navigate]);

  // Form states for tourists
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showEmailForm, setShowEmailForm] = useState(false);

  // Google OAuth Login (Always role 'user' -> always goes to /client)
  const handleGoogleLogin = async () => {
    if (googleLoading) return;
    setError(null);
    setGoogleLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/google/start?return_to=/client'), {
        method: 'GET',
        credentials: 'include',
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Google OAuth chưa sẵn sàng trên máy chủ.');
      }

      window.location.href = data.auth_url;
    } catch (err: any) {
      setError(err.message || 'Lỗi kết nối với Google.');
      setGoogleLoading(false);
    }
  };

  // Standard User Email Login
  const handleUserLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đăng nhập thất bại. Vui lòng kiểm tra lại email hoặc mật khẩu.');
      }

      loginWithData(data.access_token, data.user);
      navigate('/client', { replace: true });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Standard User Register
  const handleUserRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: email.trim(),
          password,
          full_name: fullName.trim() || email.split('@')[0],
        }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đăng ký tài khoản thất bại.');
      }

      setSuccessMsg('Đăng ký tài khoản thành công! Bạn có thể đăng nhập ngay bây giờ.');
      setIsRegister(false);
      setPassword('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-[#070A10] p-4 font-['Plus_Jakarta_Sans',sans-serif] selection:bg-indigo-600 selection:text-white relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-br from-indigo-900/20 to-blue-900/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-gradient-to-tl from-emerald-900/15 to-indigo-950/20 blur-[130px] pointer-events-none" />

      {/* Top Banner */}
      <div className="mb-6 flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold tracking-wide uppercase shadow-lg shadow-indigo-950/40">
        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
        <span>Cổng Người Dùng & Du Khách TourVoice</span>
      </div>

      <div className="w-full max-w-md z-10">
        <div className="bg-[#0E131F]/90 border border-slate-800/90 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative">
          
          {/* Brand Header */}
          <div className="text-center mb-6">
            <img
              src="/logo-ngang.png"
              alt="TourVoice Quận 4"
              className="h-12 w-auto mx-auto object-contain mb-3 drop-shadow"
            />
            <h1 className="text-xl font-black text-white tracking-tight">Khám Phá Du Lịch Số Quận 4</h1>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Đăng nhập để lưu lại các địa điểm ẩm thực, kích hoạt thuyết minh GPS tự động và trải nghiệm tour số độc đáo.
            </p>
          </div>

          {/* Status Alerts */}
          {error && (
            <div className="mb-4 p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium flex items-start space-x-2.5 animate-fadeIn">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-medium flex items-start space-x-2.5 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{successMsg}</span>
            </div>
          )}

          {/* Primary Google Login Button */}
          <div className="space-y-4">
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={googleLoading}
              className="w-full py-3.5 px-4 bg-white hover:bg-slate-100 text-slate-900 rounded-2xl font-bold shadow-xl flex items-center justify-center space-x-3 transition-all duration-200 disabled:opacity-50 text-sm group transform active:scale-[0.99]"
            >
              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>{googleLoading ? 'Đang kết nối Google...' : 'Đăng nhập nhanh bằng Google'}</span>
            </button>

            {/* Quick Explore Without Login */}
            <Link
              to="/client"
              className="w-full py-2.5 px-4 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-xl text-xs font-semibold transition-all flex items-center justify-center space-x-1.5"
            >
              <Compass className="w-3.5 h-3.5 text-indigo-400" />
              <span>Khám phá ngay không cần đăng nhập (Khách vãng lai)</span>
            </Link>

            {/* Divider */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-800"></div>
              </div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-[#0E131F] px-2 text-slate-500 font-semibold tracking-wider">
                  Hoặc bằng tài khoản email du khách
                </span>
              </div>
            </div>

            {/* Toggle Email Form Button */}
            {!showEmailForm ? (
              <button
                type="button"
                onClick={() => setShowEmailForm(true)}
                className="w-full py-2 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
              >
                Đăng nhập / Đăng ký bằng Email thường
              </button>
            ) : (
              <div className="space-y-4 pt-1 animate-fadeIn">
                {/* Tabs: Login vs Register */}
                <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
                  <button
                    type="button"
                    onClick={() => {
                      setIsRegister(false);
                      setError(null);
                    }}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                      !isRegister ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Đăng Nhập
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setIsRegister(true);
                      setError(null);
                    }}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                      isRegister ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Tạo Tài Khoản
                  </button>
                </div>

                <form onSubmit={isRegister ? handleUserRegister : handleUserLogin} className="space-y-3">
                  {isRegister && (
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                        Họ & Tên
                      </label>
                      <input
                        type="text"
                        required
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Nguyễn Văn A"
                        className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  )}

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                      Địa chỉ Email
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="tourist@example.com"
                      className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[11px] font-semibold text-slate-400">
                        Mật Khẩu
                      </label>
                      {!isRegister && (
                        <Link
                          to="/forgot-password"
                          className="text-[10px] text-indigo-400 hover:text-indigo-300"
                        >
                          Quên mật khẩu?
                        </Link>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 pr-9"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                        tabIndex={-1}
                      >
                        {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 mt-1"
                  >
                    {loading ? 'Đang xử lý...' : (isRegister ? 'Đăng Ký Tài Khoản' : 'Đăng Nhập Du Khách')}
                  </button>
                </form>
              </div>
            )}
          </div>

          {/* Bottom Admin Link: Separate Admin Login Entrance */}
          <div className="mt-8 pt-5 border-t border-slate-800/80 text-center space-y-2">
            <p className="text-[11px] text-slate-500">
              Bạn là Ban Quản Trị Hệ Thống hoặc Chủ Cơ Sở Điểm Đến?
            </p>
            <div className="flex items-center justify-center space-x-1.5 text-xs text-slate-400 hover:text-indigo-400 font-semibold transition-colors">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              <Link to="/admin/login" className="underline underline-offset-2">
                Truy cập Cổng Quản Trị Viên (/admin/login)
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
