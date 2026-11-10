import React, { lazy, Suspense } from 'react';
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
import { ArrowUpRight, Compass, Menu, UserRound } from 'lucide-react';
const TouristMap = lazy(() => import('./pages/TouristMap').then(m => ({ default: m.TouristMap })));
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
  const { user } = useAuth();
  const location = useLocation();
  const { t } = useTranslation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);
  const closeSidebar = React.useCallback(() => setMobileSidebarOpen(false), []);

  const getPageTitle = (path: string) => {
    switch (path) {
      case '/admin':
      case '/admin/dashboard':
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
      <div className="tv-console">
        <Sidebar mobileOpen={mobileSidebarOpen} onCloseMobile={closeSidebar} />
        <div className="console-stage">
          <header className="console-header">
            <div className="console-heading">
              <button type="button" onClick={() => setMobileSidebarOpen(true)} className="console-menu app-button"
                aria-expanded={mobileSidebarOpen} aria-controls="console-navigation" aria-label="Mở menu điều hướng"><Menu size={20} /></button>
              <span className="console-breadcrumb">TourVoice /</span><strong>{getPageTitle(location.pathname.replace(/\/+$/, ''))}</strong>
            </div>
            <div className="console-actions">
              <Link className="app-button console-tourist-link" to="/client"><Compass size={17} /><span>Cẩm nang</span><ArrowUpRight size={14} /></Link>
              <LanguageSwitcher compact />
              <Link className="app-button console-account" to="/account" aria-label={user?.full_name || t('nav.account')}><UserRound size={18} /></Link>
            </div>
          </header>
          <main className="console-main" key={location.pathname}>{children}</main>
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
          <Suspense fallback={<div role="status" className="p-8">Đang tải…</div>}>
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
            <Route
              path="/admin"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <Dashboard />
                </ProtectedLayout>
              }
            />
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin', 'poi_owner']}>
                  <Dashboard />
                </ProtectedLayout>
              }
            />

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
            <Route path="/" element={<Navigate to="/client" replace />} />
            <Route
              path="/pois"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
                  <POIList />
                </ProtectedLayout>
              }
            />
            <Route
              path="/tours"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
                  <Tours />
                </ProtectedLayout>
              }
            />
            <Route
              path="/qr-codes"
              element={
                <ProtectedLayout allowedRoles={['admin', 'super_admin']}>
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
        </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};
