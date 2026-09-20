import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/Login';
import { AdminLogin } from './pages/AdminLogin';
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
import './i18n';
import { useTranslation } from 'react-i18next';
import { LanguageSwitcher } from './components/LanguageSwitcher';
import { Compass, Menu } from 'lucide-react';
import { TouristMap } from './pages/TouristMap';
import { Orders } from './pages/Orders';


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
  const { t } = useTranslation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/':
        return t('header.dashboard');
      case '/pois':
        return t('header.pois');
      case '/tours':
        return t('header.tours');
      case '/qr-codes':
        return t('header.qrCodes');
      case '/orders':
        return t('header.orders');
      case '/moderation':
        return t('header.moderation');
      case '/audit-logs':
        return t('header.auditLogs');
      case '/owner':
        return t('header.owner');
      case '/account':
        return t('header.account');
      case '/account/security':
        return t('header.security');
      case '/owner/registration-status':
        return t('header.ownerStatus');
      case '/403':
        return t('header.forbidden');
      default:
        return t('header.appTitle');
    }
  };

  return (
    <ProtectedRoute
      allowedRoles={allowedRoles}
      requiredPermission={requiredPermission}
      requireOwnerVerified={requireOwnerVerified}
    >
      <div className="flex h-screen bg-[#0B0F17] text-slate-100 overflow-hidden font-['Plus_Jakarta_Sans',sans-serif] selection:bg-indigo-600 selection:text-white">
        <Sidebar mobileOpen={mobileSidebarOpen} onCloseMobile={() => setMobileSidebarOpen(false)} />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Top Header - Modern Dark Minimalist */}
          <header className="h-16 bg-[#0E131F]/95 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 flex items-center justify-between shrink-0 z-20">
            {/* Left: Mobile Hamburger & Breadcrumbs */}
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => setMobileSidebarOpen(true)}
                className="lg:hidden p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
                title="Mở menu quản trị"
                aria-label="Mở menu điều hướng"
              >
                <Menu className="w-5 h-5" />
              </button>

              {/* Breadcrumbs */}
              <div className="flex items-center space-x-2 text-xs">
                <Link to="/" className="text-slate-400 hover:text-slate-200 transition-colors font-medium hidden sm:inline">
                  TourVoice
                </Link>
                <span className="text-slate-600 font-bold hidden sm:inline">/</span>
                <span className="font-semibold text-slate-200 flex items-center space-x-2 bg-slate-900/80 px-2.5 py-1 rounded-lg border border-slate-800/80">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                  <span className="truncate max-w-[130px] sm:max-w-none">{getPageTitle(location.pathname)}</span>
                </span>
              </div>
            </div>

            {/* Right Quick Actions & User Hub */}
            <div className="flex items-center space-x-2 sm:space-x-3">
              <LanguageSwitcher />

              <Link
                to="/client"
                className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-300 hover:text-indigo-200 text-xs font-semibold border border-indigo-500/20 transition-all"
                title="Mở ứng dụng Bản đồ Khách du lịch Quận 4"
              >
                <Compass className="w-3.5 h-3.5 text-indigo-400" />
                <span>{t('header.clientMap')}</span>
              </Link>

              <Link
                to="/account"
                className="flex items-center space-x-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs transition-all shadow-sm"
              >
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-5 h-5 rounded-full object-cover ring-1 ring-slate-700" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-emerald-500/30"></span>
                )}
                <span className="font-semibold text-slate-200 max-w-[80px] sm:max-w-[120px] truncate">{user?.full_name || user?.email}</span>
                <span className="hidden sm:inline px-1.5 py-0.5 rounded-md bg-indigo-500/15 text-indigo-400 font-semibold uppercase text-[9px] border border-indigo-500/20">
                  {user?.role}
                </span>
              </Link>

              <button
                onClick={logout}
                className="text-xs text-slate-400 hover:text-rose-400 font-medium px-2 sm:px-2.5 py-1.5 rounded-xl hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all"
              >
                {t('nav.logout')}
              </button>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto bg-[#0B0F17] custom-scrollbar">{children}</main>
        </div>
      </div>

    </ProtectedRoute>
  );
};

const FallbackRoute: React.FC = () => {
  const { user } = useAuth();
  if (user?.role === 'user') {
    return <Navigate to="/client" replace />;
  }
  return <Navigate to="/" replace />;
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Tourist Client Web Routes */}
            <Route path="/client" element={<TouristMap />} />
            <Route path="/client/*" element={<TouristMap />} />
            <Route path="/tourist" element={<TouristMap />} />

            {/* Tourist Authentication Gateways */}
            <Route path="/login" element={<Login />} />
            <Route path="/client/login" element={<Login />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Isolated Admin & Business Owner Authentication Gateway */}
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<Navigate to="/" replace />} />
            <Route path="/admin/*" element={<Navigate to="/" replace />} />

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

            {/* Dashboard & Content (Admin / Super Admin / Owner ONLY) */}
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

            {/* Orders & Reconciliation (Admin only) */}
            <Route
              path="/orders"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
                  <Orders />
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

            <Route path="*" element={<FallbackRoute />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
