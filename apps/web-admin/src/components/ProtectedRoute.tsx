import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  requiredPermission?: string;
  requireOwnerVerified?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
  requiredPermission,
  requireOwnerVerified = false,
}) => {
  const { status, user, bootstrapError, retryBootstrap, hasPermission } = useAuth();
  const location = useLocation();

  // 1. Loading state: No flashing of protected or login screen
  if (status === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm text-slate-400 font-medium animate-pulse">
            Đang kiểm tra trạng thái xác thực hệ thống...
          </p>
        </div>
      </div>
    );
  }

  // 2. Network error state
  if (status === 'error') {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-900 text-white p-6">
        <div className="max-w-md w-full bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-2xl text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center mx-auto text-2xl font-bold">
            !
          </div>
          <h2 className="text-lg font-bold text-white">Lỗi Kết Nối Máy Chủ</h2>
          <p className="text-sm text-slate-300">
            {bootstrapError || 'Không thể liên lạc với máy chủ TourVoice. Vui lòng kiểm tra lại đường truyền mạng.'}
          </p>
          <button
            onClick={retryBootstrap}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-indigo-600/30 text-sm"
          >
            Thử kết nối lại
          </button>
        </div>
      </div>
    );
  }

  // 3. Anonymous: redirect to admin login for protected admin/owner routes
  if (status === 'anonymous' || !user) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  // 4. User role ('user') is strictly restricted to /client only
  if (user.role === 'user') {
    return <Navigate to="/client" replace />;
  }

  // 5. Role restrictions
  if (allowedRoles && allowedRoles.length > 0) {
    if (!allowedRoles.includes(user.role)) {
      return <Navigate to="/403" replace />;
    }
  }

  // 5. Permission check
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/403" replace />;
  }

  // 6. Owner verification check
  if (requireOwnerVerified && user.role === 'poi_owner' && !user.is_poi_owner_verified) {
    return <Navigate to="/owner/registration-status" replace />;
  }

  return <>{children}</>;
};
