import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, KeyRound, Globe, Laptop, Trash2, AlertCircle, CheckCircle2, RefreshCw, LogOut } from 'lucide-react';

interface ActiveSession {
  id: string;
  ip_address?: string;
  user_agent?: string;
  created_at?: string;
  last_used_at?: string;
  expires_at?: string;
}

export const AccountSecurity: React.FC = () => {
  const { user, fetchWithAuth, logout, logoutAll } = useAuth();

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdError, setPwdError] = useState<string | null>(null);
  const [pwdSuccess, setPwdSuccess] = useState<string | null>(null);

  // Google linking state
  const [linkLoading, setLinkLoading] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  // Sessions state
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionActionMsg, setSessionActionMsg] = useState<string | null>(null);

  const fetchSessions = async () => {
    try {
      setSessionsLoading(true);
      const res = await fetchWithAuth('/api/v1/auth/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error('Failed to fetch sessions:', e);
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError(null);
    setPwdSuccess(null);

    if (newPassword.length < 6) {
      setPwdError('Mật khẩu mới phải có ít nhất 6 ký tự.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPwdError('Mật khẩu xác nhận không khớp.');
      return;
    }

    setPwdLoading(true);
    try {
      const res = await fetchWithAuth('/api/v1/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đổi mật khẩu thất bại.');
      }

      setPwdSuccess('Đổi mật khẩu thành công! Tất cả các phiên khác đã được thu hồi. Đang đăng xuất...');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      setTimeout(() => {
        logout();
      }, 2000);
    } catch (err: any) {
      setPwdError(err.message);
    } finally {
      setPwdLoading(false);
    }
  };

  const handleStartGoogleLink = async () => {
    setLinkError(null);
    setLinkLoading(true);
    try {
      const res = await fetchWithAuth('/api/v1/auth/google/link/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ return_to: '/account/security' }),
      });
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Không thể khởi tạo liên kết Google.');
      }

      window.location.href = data.auth_url;
    } catch (err: any) {
      setLinkError(err.message);
      setLinkLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      const res = await fetchWithAuth(`/api/v1/auth/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setSessionActionMsg('Đã thu hồi phiên làm việc thành công.');
        fetchSessions();
      } else {
        const data = await res.json();
        setSessionActionMsg(`Lỗi: ${data.detail || 'Không thể thu hồi phiên.'}`);
      }
    } catch (e: any) {
      setSessionActionMsg('Lỗi khi thu hồi phiên làm việc.');
    }
  };

  const handleLogoutAll = async () => {
    if (!window.confirm('Bạn có chắc chắn muốn đăng xuất khỏi tất cả thiết bị?')) return;
    await logoutAll();
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 font-['Plus_Jakarta_Sans',sans-serif]">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Cài Đặt & Bảo Mật</h1>
        <p className="text-sm text-slate-500 mt-1">
          Quản lý mật khẩu, liên kết định danh Google OAuth và giám sát các phiên đăng nhập.
        </p>
      </div>

      {/* SECTION 1: CHANGE PASSWORD */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
            <KeyRound className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Đổi Mật Khẩu</h2>
            <p className="text-xs text-slate-500">Cập nhật mật khẩu để bảo vệ an toàn cho tài khoản.</p>
          </div>
        </div>

        {user?.has_password ? (
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            {pwdError && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{pwdError}</span>
              </div>
            )}
            {pwdSuccess && (
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 text-xs flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{pwdSuccess}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Mật khẩu hiện tại
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Mật khẩu mới
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Ít nhất 6 ký tự"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Xác nhận mật khẩu mới
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>

            <button
              type="submit"
              disabled={pwdLoading}
              className="py-2.5 px-5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-xs transition-colors shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              {pwdLoading ? 'Đang cập nhật...' : 'Cập Nhật Mật Khẩu'}
            </button>
          </form>
        ) : (
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 space-y-1">
            <p className="font-semibold text-slate-800">Tài khoản đăng nhập qua Google</p>
            <p>
              Tài khoản của bạn được khởi tạo bằng Google OpenID Connect và không lưu trữ mật khẩu nội bộ.
              Bạn có thể tiếp tục đăng nhập an toàn bằng nút Google.
            </p>
          </div>
        )}
      </div>

      {/* SECTION 2: GOOGLE ACCOUNT LINKING */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-800">Định Danh Google (OIDC)</h2>
            <p className="text-xs text-slate-500">Liên kết tài khoản Google để đăng nhập 1 chạm nhanh chóng.</p>
          </div>
        </div>

        {linkError && (
          <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-600 text-xs flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{linkError}</span>
          </div>
        )}

        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200/60">
          <div className="flex items-center space-x-3">
            <svg className="w-6 h-6 shrink-0" viewBox="0 0 24 24">
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
            <div>
              <p className="text-sm font-semibold text-slate-800">Google Account</p>
              <p className="text-xs text-slate-500">
                {user?.is_google_linked ? 'Tài khoản đã được liên kết bảo mật.' : 'Chưa liên kết tài khoản Google nào.'}
              </p>
            </div>
          </div>

          {user?.is_google_linked ? (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Đã liên kết</span>
            </span>
          ) : (
            <button
              onClick={handleStartGoogleLink}
              disabled={linkLoading}
              className="py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
            >
              {linkLoading ? 'Đang khởi tạo...' : 'Liên Kết Ngay'}
            </button>
          )}
        </div>
      </div>

      {/* SECTION 3: ACTIVE SESSIONS */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Laptop className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-800">Phiên Hoạt Động Của Bạn</h2>
              <p className="text-xs text-slate-500">
                Danh sách các thiết bị và phiên làm việc đang có hiệu lực.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={fetchSessions}
              className="p-2 text-slate-500 hover:text-indigo-600 rounded-lg hover:bg-slate-100 transition-colors"
              title="Làm mới"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={handleLogoutAll}
              className="flex items-center space-x-1.5 py-1.5 px-3 rounded-lg bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Đăng xuất tất cả thiết bị</span>
            </button>
          </div>
        </div>

        {sessionActionMsg && (
          <div className="p-3 rounded-xl bg-slate-100 text-xs text-slate-700 font-medium">
            {sessionActionMsg}
          </div>
        )}

        <div className="overflow-x-auto">
          {sessionsLoading ? (
            <p className="text-xs text-slate-400 py-4 text-center">Đang tải danh sách phiên...</p>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">Không có phiên đăng nhập nào khác.</p>
          ) : (
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 font-semibold">Thiết bị / Trình duyệt</th>
                  <th className="py-2.5 font-semibold">Địa chỉ IP</th>
                  <th className="py-2.5 font-semibold">Hoạt động gần nhất</th>
                  <th className="py-2.5 font-semibold text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/80">
                    <td className="py-3 font-medium text-slate-700 max-w-xs truncate" title={s.user_agent}>
                      {s.user_agent ? s.user_agent.split(')')[0] + ')' : 'Trình duyệt Web'}
                    </td>
                    <td className="py-3 font-mono text-slate-500">{s.ip_address || '127.0.0.1'}</td>
                    <td className="py-3 text-slate-500">
                      {s.last_used_at ? new Date(s.last_used_at).toLocaleString('vi-VN') : 'Vừa xong'}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleRevokeSession(s.id)}
                        className="inline-flex items-center space-x-1 text-red-600 hover:text-red-700 font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Thu hồi</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
