import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { 
  ShieldCheck, 
  Lock, 
  Store, 
  ArrowRight, 
  CheckCircle2, 
  Eye, 
  EyeOff, 
  AlertCircle,
  Compass,
  Building2,
  KeyRound,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';

export const AdminLogin: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loginWithData, logout } = useAuth();

  // Determine safe redirect target
  const fromPath = (location.state as any)?.from?.pathname || '/';

  // If already logged in as Admin / Owner -> go to Dashboard
  useEffect(() => {
    if (user && (user.role === 'admin' || user.role === 'super_admin' || user.role === 'poi_owner')) {
      navigate(fromPath === '/admin/login' || fromPath === '/login' ? '/' : fromPath, { replace: true });
    }
  }, [user, navigate, fromPath]);

  // Tab: 'login' (Admin/Owner) vs 'register_owner' (Chủ quán đăng ký)
  const [activeTab, setActiveTab] = useState<'login' | 'register_owner'>('login');

  // Form states
  const [email, setEmail] = useState('admin@tourvoice.vn');
  const [password, setPassword] = useState('Admin@123456');
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState('');
  const [businessName, setBusinessName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Admin login handler
  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/admin/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đăng nhập quản trị thất bại. Vui lòng kiểm tra lại tài khoản.');
      }

      loginWithData(data.access_token, data.user);
      
      if (data.user.role === 'poi_owner' && !data.user.is_poi_owner_verified) {
        navigate('/owner/registration-status', { replace: true });
      } else {
        const dest = fromPath === '/admin/login' || fromPath === '/login' ? '/' : fromPath;
        navigate(dest, { replace: true });
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // POI Owner Registration handler
  const handleRegisterOwner = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await fetch(apiUrl('/auth/register-owner'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          business_name: businessName.trim(),
        }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đăng ký xét duyệt thất bại.');
      }

      setSuccessMsg('Đăng ký thành công! Hồ sơ cơ sở của bạn đã được chuyển đến Ban Quản trị để xét duyệt và cấp quyền.');
      setActiveTab('login');
      setPassword('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070A10] flex flex-col justify-center items-center p-4 selection:bg-indigo-600 selection:text-white relative overflow-hidden font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Background Decorative Gradients */}
      <div className="absolute top-[-15%] left-[-10%] w-[55%] h-[55%] rounded-full bg-gradient-to-br from-indigo-900/25 to-blue-900/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-15%] right-[-10%] w-[55%] h-[55%] rounded-full bg-gradient-to-tl from-purple-900/20 to-indigo-950/20 blur-[130px] pointer-events-none" />

      {/* Top Security Banner */}
      <div className="mb-6 flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold tracking-wide uppercase shadow-lg shadow-indigo-950/40">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <KeyRound className="w-3.5 h-3.5 text-indigo-400" />
        <span>Cổng Quản Trị Hệ Thống Bảo Mật (Admin Console)</span>
      </div>

      <div className="w-full max-w-md z-10">
        {/* Main Card Container */}
        <div className="bg-[#0E131F]/90 border border-slate-800/90 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl relative">
          {/* Header Title */}
          <div className="text-center mb-6">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-indigo-500 p-0.5 shadow-xl shadow-indigo-600/30 mx-auto mb-4 flex items-center justify-center">
              <div className="w-full h-full bg-[#0E131F] rounded-[14px] flex items-center justify-center">
                <ShieldCheck className="w-7 h-7 text-indigo-400" />
              </div>
            </div>
            <h1 className="text-2xl font-black text-white tracking-tight">TourVoice Console</h1>
            <p className="text-xs text-slate-400 mt-1.5">
              Dành riêng cho Ban Quản Trị Hệ Thống & Chủ Cơ Sở Đã Xác Minh
            </p>
          </div>

          {/* Warning notice if a regular Google 'user' is already logged in */}
          {user && user.role === 'user' && (
            <div className="mb-6 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-left space-y-3">
              <div className="flex items-start space-x-2.5">
                <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-amber-300">Tài Khoản Không Có Quyền Quản Trị</h4>
                  <p className="text-[11px] text-slate-300 mt-0.5 leading-relaxed">
                    Bạn hiện đang đăng nhập dưới tài khoản <strong className="text-white">{user.email}</strong> với vai trò <span className="underline font-semibold">Người Dùng / Du Khách</span>.
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2 pt-1">
                <Link
                  to="/client"
                  className="flex-1 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl text-center transition-all flex items-center justify-center space-x-1"
                >
                  <Compass className="w-3.5 h-3.5" />
                  <span>Vào Trang Du Khách (/client)</span>
                </Link>
                <button
                  onClick={logout}
                  className="py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition-all flex items-center justify-center space-x-1"
                  title="Đăng xuất để đổi tài khoản"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Đổi tài khoản</span>
                </button>
              </div>
            </div>
          )}

          {/* Tab Switcher: Admin Login vs Register Owner */}
          <div className="flex rounded-2xl bg-slate-950/80 p-1 border border-slate-800/80 mb-6">
            <button
              type="button"
              onClick={() => {
                setActiveTab('login');
                setError(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl transition-all flex items-center justify-center space-x-1.5 ${
                activeTab === 'login'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              <span>Đăng Nhập Quản Trị</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('register_owner');
                setError(null);
                setSuccessMsg(null);
              }}
              className={`flex-1 py-2.5 text-xs font-bold rounded-xl transition-all flex items-center justify-center space-x-1.5 ${
                activeTab === 'register_owner'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Store className="w-3.5 h-3.5" />
              <span>Đăng Ký Chủ Cơ Sở</span>
            </button>
          </div>

          {/* Alerts */}
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

          {/* Mode 1: Admin / Owner Login Form */}
          {activeTab === 'login' && (
            <form onSubmit={handleAdminLogin} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                  Email Quản Trị / Chủ Cơ Sở
                </label>
                <div className="relative">
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@tourvoice.vn"
                    className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Mật Khẩu Xác Thực
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    Quên mật khẩu?
                  </Link>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 text-white rounded-xl text-xs font-bold shadow-xl shadow-indigo-600/30 transition-all duration-200 flex items-center justify-center space-x-2 disabled:opacity-50 mt-2 active:scale-[0.99]"
              >
                {loading ? (
                  <span>Đang kiểm tra bảo mật...</span>
                ) : (
                  <>
                    <span>Đăng Nhập Quản Trị Hệ Thống</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Mode 2: POI Owner Registration Form */}
          {activeTab === 'register_owner' && (
            <form onSubmit={handleRegisterOwner} className="space-y-3.5">
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Họ & Tên Đại Diện Cơ Sở
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nguyễn Văn A"
                  className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Tên Cơ Sở Kinh Doanh / Điểm Đến
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="Quán Ốc Oanh - Phố Vĩnh Khánh"
                    className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-all"
                  />
                  <Building2 className="w-4 h-4 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2" />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Email Đăng Ký Tài Khoản
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="owner@cuahang.vn"
                  className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Mật Khẩu Thiết Lập
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Tối thiểu 6 ký tự"
                    className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-white text-xs placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 transition-all pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-xl shadow-emerald-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 mt-2"
              >
                {loading ? (
                  <span>Đang gửi hồ sơ...</span>
                ) : (
                  <>
                    <span>Gửi Hồ Sơ Xét Duyệt Chủ Cơ Sở</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Bottom Security Footer Info */}
          <div className="mt-8 pt-5 border-t border-slate-800/80 text-center space-y-3">
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Khu vực bảo mật nội bộ. Tuyệt đối không chia sẻ tài khoản quản trị viên.
            </p>
            <div className="flex items-center justify-center space-x-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition-colors">
              <Compass className="w-3.5 h-3.5" />
              <Link to="/client">
                Bạn là Du khách? Bấm vào đây để đến Bản Đồ Du Lịch (/client)
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
