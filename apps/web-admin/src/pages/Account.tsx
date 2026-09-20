import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Shield, CheckCircle2, AlertCircle, KeyRound, ExternalLink } from 'lucide-react';
import { PageHeader, Badge, Card } from '../components/ui';

export const Account: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto space-y-6 font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Header */}
      <PageHeader
        title="Thông Tin Tài Khoản"
        description="Quản lý thông tin định danh và quyền hạn của bạn trên hệ thống TourVoice"
      />

      {/* Main Profile Card */}
      <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 md:p-8 shadow-2xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-5">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt="Avatar"
              className="w-20 h-20 rounded-2xl object-cover border-2 border-indigo-500/30 shadow-lg"
            />
          ) : (
            <div className="w-20 h-20 rounded-2xl bg-indigo-600 text-white flex items-center justify-center text-3xl font-bold shadow-lg shadow-indigo-600/30">
              {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
            </div>
          )}

          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <h2 className="text-xl font-bold text-white">{user.full_name || 'Người dùng'}</h2>
              <Badge variant="purple" size="sm">
                {user.role}
              </Badge>
            </div>
            <p className="text-sm text-slate-400 flex items-center space-x-1.5">
              <Mail className="w-4 h-4 text-slate-500" />
              <span>{user.email}</span>
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-800/80">
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Xác thực Email
            </span>
            <div className="flex items-center space-x-2 text-sm font-medium text-slate-200">
              {user.is_verified ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">Đã xác thực</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                  <span className="text-amber-400">Chưa xác thực</span>
                </>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Trạng thái Chủ Quán (POI Owner)
            </span>
            <div className="flex items-center space-x-2 text-sm font-medium text-slate-200">
              {user.role === 'poi_owner' ? (
                user.is_poi_owner_verified ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">Đã được Admin duyệt</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-amber-400" />
                    <span className="text-amber-400">Đang chờ xét duyệt hồ sơ</span>
                  </>
                )
              ) : (
                <span className="text-slate-500">Không áp dụng</span>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Phương thức xác thực
            </span>
            <div className="text-sm font-medium text-slate-300">
              {user.is_google_linked && user.has_password && 'Google + Mật khẩu'}
              {user.is_google_linked && !user.has_password && 'Chỉ đăng nhập bằng Google'}
              {!user.is_google_linked && user.has_password && 'Chỉ dùng Mật khẩu'}
              {!user.is_google_linked && !user.has_password && 'Chưa cấu hình mật khẩu'}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Cài đặt Bảo mật
            </span>
            <div>
              <Link
                to="/account/security"
                className="inline-flex items-center space-x-1.5 text-sm font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <KeyRound className="w-4 h-4" />
                <span>Đổi mật khẩu & Quản lý phiên</span>
                <ExternalLink className="w-3.5 h-3.5 ml-0.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Permissions catalog */}
        <div className="pt-4 border-t border-slate-800/80">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Quyền Hạn Đang Sở Hữu ({user.permissions?.length || 0})
          </h3>
          <div className="flex flex-wrap gap-2">
            {user.permissions?.map((perm) => (
              <span
                key={perm}
                className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs font-mono font-medium"
              >
                {perm}
              </span>
            ))}
            {(!user.permissions || user.permissions.length === 0) && (
              <span className="text-xs text-slate-500 italic">Tài khoản chưa được gán quyền hạn nâng cao.</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
