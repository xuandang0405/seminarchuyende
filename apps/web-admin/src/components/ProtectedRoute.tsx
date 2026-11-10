import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AuthFrame } from './AuthFrame';
import { Button } from './ui';

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
      <AuthFrame title="Đang kiểm tra phiên"><p role="status" className="auth-message">Đang xác thực tài khoản…</p></AuthFrame>
    );
  }

  // 2. Network error state
  if (status === 'error') {
    return (
      <AuthFrame title="Chưa kết nối được">
        <div className="auth-form"><p className="auth-error" role="alert">{bootstrapError || 'Máy chủ TourVoice chưa phản hồi.'}</p>
          <Button onClick={retryBootstrap}>Thử lại</Button></div>
      </AuthFrame>
    );
  }

  // 3. Anonymous: redirect to admin login for protected admin/owner routes
  if (status === 'anonymous' || !user) {
    const account = location.pathname === '/account' || location.pathname.startsWith('/account/');
    return <Navigate to={account ? '/client/login' : '/admin/login'} state={{ from: location }} replace />;
  }

  // 4. User role ('user') is not allowed in admin routes: redirect to /admin/login
  if (user.role === 'user' && allowedRoles && !allowedRoles.includes('user')) {
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
