import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { User, Mail, Shield, CheckCircle2, AlertCircle, KeyRound, ExternalLink } from 'lucide-react';

export const Account: React.FC = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Thông Tin Tài Khoản</h1>
        <p className="text-sm text-slate-500 mt-1">
          Quản lý thông tin định danh và quyền hạn của bạn trên hệ thống TourVoice.
        </p>
      </div>

      {/* Main Profile Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm space-y-6">
        <div className="flex items-center space-x-5">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt="Avatar"
              className="w-20 h-20 rounded-2xl object-cover border-2 border-indigo-100 shadow-md"
            />
          ) : (
            <div className="w-20 h-20 rounded-2xl bg-indigo-600 text-white flex items-center justify-center text-3xl font-bold shadow-md shadow-indigo-600/20">
              {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
            </div>
          )}

          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <h2 className="text-xl font-bold text-slate-800">{user.full_name || 'Người dùng'}</h2>
              <span className="px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-bold uppercase text-xs">
                {user.role}
              </span>
            </div>
            <p className="text-sm text-slate-500 flex items-center space-x-1.5">
              <Mail className="w-4 h-4 text-slate-400" />
              <span>{user.email}</span>
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Xác thực Email
            </span>
            <div className="flex items-center space-x-2 text-sm font-medium text-slate-700">
              {user.is_verified ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span>Đã xác thực</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  <span>Chưa xác thực</span>
                </>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Trạng thái Chủ Quán (POI Owner)
            </span>
            <div className="flex items-center space-x-2 text-sm font-medium text-slate-700">
              {user.role === 'poi_owner' ? (
                user.is_poi_owner_verified ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Đã được Admin duyệt</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-amber-500" />
                    <span>Đang chờ xét duyệt hồ sơ</span>
                  </>
                )
              ) : (
                <span className="text-slate-400">Không áp dụng</span>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Phương thức xác thực
            </span>
            <div className="text-sm font-medium text-slate-700">
              {user.is_google_linked && user.has_password && 'Google + Mật khẩu'}
              {user.is_google_linked && !user.has_password && 'Chỉ đăng nhập bằng Google'}
              {!user.is_google_linked && user.has_password && 'Chỉ dùng Mật khẩu'}
              {!user.is_google_linked && !user.has_password && 'Chưa cấu hình mật khẩu'}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/60 space-y-1">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Cài đặt Bảo mật
            </span>
            <div>
              <Link
                to="/account/security"
                className="inline-flex items-center space-x-1.5 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition-colors"
              >
                <KeyRound className="w-4 h-4" />
                <span>Đổi mật khẩu & Quản lý phiên</span>
                <ExternalLink className="w-3.5 h-3.5 ml-0.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Permissions catalog */}
        <div className="pt-4 border-t border-slate-100">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Quyền Hạn Đang Sở Hữu ({user.permissions?.length || 0})
          </h3>
          <div className="flex flex-wrap gap-2">
            {user.permissions?.map((perm) => (
              <span
                key={perm}
                className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-xs font-mono font-medium"
              >
                {perm}
              </span>
            ))}
            {(!user.permissions || user.permissions.length === 0) && (
              <span className="text-xs text-slate-400 italic">Tài khoản chưa được gán quyền hạn nâng cao.</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
