import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MapPin, 
  Route, 
  QrCode, 
  CheckSquare, 
  Store, 
  FileText, 
  LogOut, 
  ShieldCheck,
  Receipt, 
  User, 
  Shield, 
  Compass, 
  ChevronLeft, 
  ChevronRight,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ mobileOpen = false, onCloseMobile }) => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);

  const isStaff = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'poi_owner';

  interface NavSection {
    title: string;
    items: {
      to: string;
      label: string;
      icon: React.ComponentType<{ className?: string }>;
      badge?: string;
    }[];
  }

  const sections: NavSection[] = [
    {
      title: 'Tổng quan',
      items: [
        { to: '/', label: t('nav.dashboard') || 'Bảng điều khiển', icon: LayoutDashboard },
        { to: '/client', label: t('nav.touristMap') || 'Bản đồ du khách', icon: Compass, badge: 'Live' },
      ],
    },
    {
      title: 'Quản lý du lịch',
      items: [
        { to: '/pois', label: t('nav.pois') || 'Địa điểm POI', icon: MapPin },
        ...(isStaff
          ? [
              { to: '/tours', label: t('nav.tours') || 'Tuyến tham quan', icon: Route },
              { to: '/qr-codes', label: t('nav.qrCodes') || 'Mã QR điểm đến', icon: QrCode },
            ]
          : []),
      ],
    },
  ];

  if (user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'poi_owner') {
    const opsItems = [];
    if (user?.role === 'admin' || user?.role === 'super_admin') {
      opsItems.push(
        { to: '/orders', label: t('nav.orders') || 'Đơn hàng & Vé', icon: Receipt },
        { to: '/moderation', label: t('nav.moderation') || 'Kiểm duyệt nội dung', icon: CheckSquare },
        { to: '/audit-logs', label: t('nav.auditLogs') || 'Nhật ký hệ thống', icon: FileText }
      );
    }
    if (user?.role === 'poi_owner') {
      opsItems.push({ to: '/owner', label: t('nav.ownerPortal') || 'Cổng chủ quán', icon: Store });
    }
    sections.push({
      title: 'Vận hành & Kinh doanh',
      items: opsItems,
    });
  }

  sections.push({
    title: 'Hệ thống & Tài khoản',
    items: [
      { to: '/account', label: t('nav.account') || 'Tài khoản', icon: User },
      { to: '/account/security', label: t('nav.security') || 'Bảo mật & 2FA', icon: Shield },
    ],
  });

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/75 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300"
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 lg:static lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${
          collapsed ? 'w-20' : 'w-64'
        } bg-[#080C14] border-r border-slate-800/80 flex flex-col justify-between shrink-0 transition-all duration-300 ease-in-out select-none shadow-2xl lg:shadow-none`}
      >
        <div className="flex flex-col flex-1 min-h-0">
          {/* Brand Header with Logo */}
          <div className="h-16 px-4 border-b border-slate-800/80 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-3 overflow-hidden">
              {collapsed ? (
                <img
                  src="/logo-vuong.png"
                  alt="TourVoice"
                  className="w-9 h-9 rounded-xl object-contain shrink-0 ring-1 ring-slate-800"
                />
              ) : (
                <div className="flex items-center gap-2 overflow-hidden">
                  <img
                    src="/logo-ngang.png"
                    alt="TourVoice Quận 4"
                    className="h-8 w-auto object-contain max-w-[155px]"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center space-x-1">
              {/* Desktop Collapse Button */}
              <button
                onClick={() => setCollapsed(!collapsed)}
                className="hidden lg:flex w-7 h-7 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white items-center justify-center transition-colors shrink-0"
                title={collapsed ? 'Mở rộng menu' : 'Thu nhỏ menu'}
              >
                {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
              </button>

              {/* Mobile Close Button */}
              <button
                onClick={onCloseMobile}
                className="lg:hidden w-7 h-7 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white flex items-center justify-center transition-colors shrink-0"
                title="Đóng menu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

        {/* Navigation Sections */}
        <div className="p-3 space-y-6 overflow-y-auto flex-1 custom-scrollbar">
          {sections.map((section, idx) => (
            <div key={idx} className="space-y-1">
              {!collapsed && (
                <div className="px-3 text-[10px] font-semibold text-slate-500 tracking-wider uppercase">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => onCloseMobile?.()}
                  className={({ isActive }) =>
                    `group relative flex items-center ${
                      collapsed ? 'justify-center px-2 py-2.5' : 'space-x-3 px-3 py-2.5'
                    } rounded-xl text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/80'
                    }`
                  }
                  title={collapsed ? item.label : undefined}
                >
                  {({ isActive }) => (
                    <>
                      <item.icon
                        className={`w-4 h-4 shrink-0 transition-transform ${
                          isActive ? 'text-white' : 'text-slate-400 group-hover:text-indigo-400'
                        }`}
                      />
                      {!collapsed && (
                        <span className="truncate flex-1 font-medium tracking-wide">
                          {item.label}
                        </span>
                      )}
                      {!collapsed && item.badge && (
                        <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* User Footer Profile */}
      <div className="p-3 border-t border-slate-800/80 bg-[#060910] shrink-0">
        {!collapsed ? (
          <div className="space-y-2">
            <div className="flex items-center space-x-2.5 px-2.5 py-2 rounded-xl bg-slate-900/60 border border-slate-800/80">
              <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="truncate flex-1">
                <p className="text-xs font-semibold text-slate-200 truncate capitalize">
                  {user?.role ? user.role.replace('_', ' ') : 'Người dùng'}
                </p>
                <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
              </div>
            </div>

            <button
              onClick={logout}
              className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition-all hover:border-rose-500/30"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>{t('nav.logout') || 'Đăng xuất'}</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center space-y-2">
            <div
              className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-indigo-400"
              title={`${user?.role}: ${user?.email}`}
            >
              <ShieldCheck className="w-4 h-4" />
            </div>
            <button
              onClick={logout}
              className="w-8 h-8 rounded-xl text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 flex items-center justify-center transition-colors"
              title={t('nav.logout') || 'Đăng xuất'}
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </aside>
  </>
  );
};
