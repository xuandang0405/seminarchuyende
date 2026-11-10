import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { Brand, HarborArt } from './Brand';

export function AuthFrame({ title, description, children, back = '/client', backLabel = 'Về cẩm nang', console = false }: {
  title: string; description?: string; children: ReactNode; back?: string; backLabel?: string; console?: boolean;
}) {
  return <main className={`auth-frame${console ? ' is-console' : ''}`}>
    <div className="auth-main">
      <div className="auth-top"><Brand subtitle={console ? 'Không gian quản trị' : 'Cẩm nang Quận 4'} />
        <Link to={back} className="auth-link"><ArrowLeft size={16} /> {backLabel}</Link></div>
      <section className="auth-card" aria-labelledby="auth-title">
        <p className="auth-kicker">{console ? 'TOURVOICE QUẢN TRỊ' : 'TÀI KHOẢN TOURVOICE'}</p>
        <h1 id="auth-title">{title}</h1>
        {description && <p className="auth-description">{description}</p>}
        {children}
      </section>
    </div>
    <div className="auth-art" aria-hidden="true">
      <HarborArt /><div><p>SỔ TAY ĐI BỘ · QUẬN 4</p><strong>Quận 4 qua từng<br /> câu chuyện</strong></div>
    </div>
  </main>;
}

export function PasswordField({ value, onChange, autoComplete = 'current-password', minimum }: {
  value: string; onChange: (value: string) => void; autoComplete?: 'new-password' | 'current-password'; minimum?: number;
}) {
  const [show, setShow] = useState(false);
  return <div>
    <label htmlFor="auth-password" className="field-label">Mật khẩu</label>
    <div className="auth-password">
      <input id="auth-password" className="field-input" type={show ? 'text' : 'password'} required minLength={minimum}
        autoComplete={autoComplete} value={value} onChange={event => onChange(event.target.value)} />
      <button type="button" className="app-button" data-variant="ghost" onClick={() => setShow(value => !value)}
        aria-label={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
    </div>
  </div>;
}
