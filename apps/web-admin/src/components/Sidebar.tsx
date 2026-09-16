import React from 'react';
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
  Headphones,
  User,
  Shield,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();

  const navItems = [
    { to: '/', label: 'Bảng Điều Khiển', icon: LayoutDashboard },
    { to: '/pois', label: 'Quản Lý POI', icon: MapPin },
    { to: '/tours', label: 'Lộ Trình Tour', icon: Route },
    { to: '/qr-codes', label: 'Mã QR Thuyết Minh', icon: QrCode },
  ];

  if (user?.role === 'admin' || user?.role === 'super_admin') {
    navItems.push({ to: '/moderation', label: 'Kiểm Duyệt', icon: CheckSquare });
    navItems.push({ to: '/audit-logs', label: 'Nhật Ký Hệ Thống', icon: FileText });
  }

  if (user?.role === 'poi_owner') {
    navItems.push({ to: '/owner', label: 'Quán Của Tôi', icon: Store });
  }

  // Account & Security links
  navItems.push({ to: '/account', label: 'Tài Khoản', icon: User });
  navItems.push({ to: '/account/security', label: 'Bảo Mật', icon: Shield });

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0">
      <div>
        <div className="p-6 border-b border-slate-800/80 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
            <Headphones className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight">TourVoice</h1>
            <p className="text-xs text-indigo-400 font-medium">Quản Trị Du Lịch Quận 4</p>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-800/80">
        <div className="px-4 py-3 bg-slate-900 rounded-xl mb-3 border border-slate-800">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-slate-200 capitalize">
              {user?.role.replace('_', ' ')}
            </span>
          </div>
          <p className="text-xs text-slate-400 truncate mt-1">{user?.email}</p>
        </div>

        <button
          onClick={logout}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Đăng Xuất</span>
        </button>
      </div>
    </aside>
  );
};
