import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Home } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Forbidden: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4 font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="max-w-md w-full bg-white border border-slate-200/80 rounded-3xl p-8 shadow-sm text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 text-amber-600 flex items-center justify-center mx-auto">
          <ShieldAlert className="w-9 h-9" />
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">403 - Quyền Truy Cập Bị Từ Chối</h1>
          <p className="text-sm text-slate-500">
            Tài khoản của bạn (<span className="font-semibold text-slate-700">{user?.email}</span>) với vai trò{' '}
            <span className="font-bold text-indigo-600 uppercase text-xs">{user?.role}</span> không có quyền truy cập vào tài nguyên này.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-2">
          <Link
            to="/account"
            className="flex-1 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition-colors flex items-center justify-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Xem tài khoản của bạn</span>
          </Link>
          <Link
            to="/"
            className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-xs transition-colors flex items-center justify-center space-x-2 shadow-md shadow-indigo-600/20"
          >
            <Home className="w-4 h-4" />
            <span>Về trang chủ</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
