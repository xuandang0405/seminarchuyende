import { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, MapPin, Route, QrCode, CheckSquare, Store, FileText, LogOut, Receipt, UserRound, Shield, Compass, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Brand } from './Brand';

export function Sidebar({ mobileOpen, onCloseMobile }: { mobileOpen: boolean; onCloseMobile: () => void }) {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const current = useLocation().pathname.replace(/\/+$/, '');
  const close = useRef<HTMLButtonElement>(null);
  const staff = user?.role === 'admin' || user?.role === 'super_admin';
  const owner = user?.role === 'poi_owner';
  useEffect(() => {
    if (!mobileOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') onCloseMobile(); };
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('keydown', escape); previous?.focus(); };
  }, [mobileOpen, onCloseMobile]);
  const sections = [
    { name: 'Không gian làm việc', items: [
      ...(owner ? [{ to: '/owner', name: t('nav.ownerPortal'), Icon: Store }] : []),
      ...(staff || owner ? [{ to: '/admin', name: t('nav.dashboard'), Icon: LayoutDashboard }] : []),
      { to: '/client', name: 'Cẩm nang du khách', Icon: Compass },
    ] },
    ...(staff ? [
      { name: 'Nội dung', items: [
        { to: '/pois', name: t('nav.pois'), Icon: MapPin },
        { to: '/tours', name: t('nav.tours'), Icon: Route },
        { to: '/qr-codes', name: t('nav.qrCodes'), Icon: QrCode },
      ] },
      { name: 'Vận hành', items: [
        { to: '/orders', name: t('nav.orders'), Icon: Receipt },
        { to: '/moderation', name: t('nav.moderation'), Icon: CheckSquare },
        { to: '/audit-logs', name: t('nav.auditLogs'), Icon: FileText },
      ] },
    ] : []),
    { name: 'Tài khoản', items: [
      { to: '/account', name: t('nav.account'), Icon: UserRound },
      { to: '/account/security', name: t('nav.security'), Icon: Shield },
    ] },
  ];
  const role = owner ? 'Chủ cơ sở' : staff ? 'Quản trị viên' : 'Du khách';
  return <>
    {mobileOpen && <button type="button" className="console-scrim" aria-label="Đóng điều hướng" onClick={onCloseMobile} />}
    <aside className={`console-sidebar${mobileOpen ? ' is-open' : ''}`} id="console-navigation">
      <div className="console-sidebar-brand"><Brand to={staff ? '/admin' : owner ? '/owner' : '/client'} subtitle={staff ? 'Không gian quản trị' : owner ? 'Cổng cơ sở' : 'Cẩm nang Quận 4'} />
        <button type="button" className="console-close app-button" ref={close} aria-label="Đóng menu" onClick={onCloseMobile}><X size={20} /></button>
      </div>
      <nav className="console-nav" aria-label="Điều hướng tài khoản">
        {sections.map(section => <div key={section.name} className="console-nav-group">
          <p>{section.name}</p>
          {section.items.map(({ to, name, Icon }) => <Link to={to} key={to} onClick={onCloseMobile}
            aria-current={current === to || to === '/admin' && current === '/admin/dashboard' ? 'page' : undefined}>
            <Icon size={18} /><span>{name}</span></Link>)}
        </div>)}
      </nav>
      <div className="console-profile">
        <span className="console-avatar"><UserRound size={19} /></span>
        <span><strong>{user?.full_name || role}</strong><small>{role}</small></span>
        <button type="button" className="app-button" data-variant="ghost" aria-label={t('nav.logout')} title={t('nav.logout')} onClick={() => void logout()}><LogOut size={18} /></button>
      </div>
    </aside>
  </>;
}
