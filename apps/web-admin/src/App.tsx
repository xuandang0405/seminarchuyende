import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/Login';
import { AuthCallback } from './pages/AuthCallback';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { Account } from './pages/Account';
import { AccountSecurity } from './pages/AccountSecurity';
import { OwnerRegistrationStatus } from './pages/OwnerRegistrationStatus';
import { Forbidden } from './pages/Forbidden';
import { Dashboard } from './pages/Dashboard';
import { POIList } from './pages/POIList';
import { Tours } from './pages/Tours';
import { QRCodes } from './pages/QRCodes';
import { Moderation } from './pages/Moderation';
import { AuditLogs } from './pages/AuditLogs';
import { OwnerPortal } from './pages/OwnerPortal';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ProtectedLayout: React.FC<{
  children: React.ReactNode;
  allowedRoles?: string[];
  requiredPermission?: string;
  requireOwnerVerified?: boolean;
}> = ({ children, allowedRoles, requiredPermission, requireOwnerVerified }) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/':
        return 'Bảng Điều Khiển Tổng Quan';
      case '/pois':
        return 'Danh Sách Địa Điểm (POI) Quận 4';
      case '/tours':
        return 'Quản Lý Tuyến Du Lịch';
      case '/qr-codes':
        return 'Quản Lý Mã QR Thuyết Minh';
      case '/moderation':
        return 'Trung Tâm Kiểm Duyệt Nội Dung';
      case '/audit-logs':
        return 'Nhật Ký Kiểm Toán Hệ Thống';
      case '/owner':
        return 'Cổng Thông Tin Chủ Quán';
      case '/account':
        return 'Hồ Sơ & Thông Tin Tài Khoản';
      case '/account/security':
        return 'Cài Đặt An Toàn & Bảo Mật';
      case '/owner/registration-status':
        return 'Tiến Trình Xét Duyệt Chủ Quán';
      case '/403':
        return 'Từ Chối Quyền Truy Cập (403)';
      default:
        return 'Hệ Thống TourVoice';
    }
  };

  return (
    <ProtectedRoute
      allowedRoles={allowedRoles}
      requiredPermission={requiredPermission}
      requireOwnerVerified={requireOwnerVerified}
    >
      <div className="flex h-screen bg-slate-50 overflow-hidden font-['Plus_Jakarta_Sans',sans-serif]">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Top Header */}
          <header className="h-16 bg-white border-b border-slate-200/80 px-8 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-3">
              <span className="text-sm font-semibold text-slate-800">
                {getPageTitle(location.pathname)}
              </span>
            </div>

            <div className="flex items-center space-x-4">
              <Link
                to="/account"
                className="flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200/70 border border-slate-200 text-xs transition-colors"
              >
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-5 h-5 rounded-full object-cover" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                )}
                <span className="font-semibold text-slate-800">{user?.full_name || user?.email}</span>
                <span className="px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-bold uppercase text-[10px]">
                  {user?.role}
                </span>
              </Link>
              <button
                onClick={logout}
                className="text-xs text-slate-500 hover:text-red-600 font-medium px-2.5 py-1.5 rounded-lg hover:bg-red-50 transition-colors"
              >
                Đăng xuất
              </button>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto p-8">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Unauthenticated Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* General Authenticated Routes */}
            <Route
              path="/account"
              element={
                <ProtectedLayout>
                  <Account />
                </ProtectedLayout>
              }
            />
            <Route
              path="/account/security"
              element={
                <ProtectedLayout>
                  <AccountSecurity />
                </ProtectedLayout>
              }
            />
            <Route
              path="/owner/registration-status"
              element={
                <ProtectedLayout>
                  <OwnerRegistrationStatus />
                </ProtectedLayout>
              }
            />
            <Route
              path="/403"
              element={
                <ProtectedLayout>
                  <Forbidden />
                </ProtectedLayout>
              }
            />

            {/* Dashboard & Content (Admin / Owner) */}
            <Route
              path="/"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <Dashboard />
                </ProtectedLayout>
              }
            />
            <Route
              path="/pois"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <POIList />
                </ProtectedLayout>
              }
            />
            <Route
              path="/tours"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <Tours />
                </ProtectedLayout>
              }
            />
            <Route
              path="/qr-codes"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <QRCodes />
                </ProtectedLayout>
              }
            />

            {/* Moderation & Audit Logs (Admin only) */}
            <Route
              path="/moderation"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
                  <Moderation />
                </ProtectedLayout>
              }
            />
            <Route
              path="/audit-logs"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
                  <AuditLogs />
                </ProtectedLayout>
              }
            />

            {/* Owner Portal (POI Owner verified or Admin) */}
            <Route
              path="/owner"
              element={
                <ProtectedLayout
                  allowedRoles={['poi_owner', 'admin', 'super_admin']}
                  requireOwnerVerified={true}
                >
                  <OwnerPortal />
                </ProtectedLayout>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
