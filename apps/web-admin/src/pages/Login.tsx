import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, Shield } from 'lucide-react';
import { AuthFrame, PasswordField } from '../components/AuthFrame';
import { Button } from '../components/ui';
import { useAuth, type UserProfile } from '../context/AuthContext';
import { apiClient } from '../services/apiClient';

export function Login() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loginWithData } = useAuth();
  const tour = new URLSearchParams(location.search).get('tour');
  const exploreUrl = tour ? '/client?tour=' + encodeURIComponent(tour) : '/client';
  const requested = location.state?.from?.pathname;
  const returnTo = requested === '/account' || requested === '/account/security' ? requested : exploreUrl;
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState<'email' | 'google' | ''>('');

  useEffect(() => {
    if (user) navigate(user.role === 'user' ? returnTo : '/admin', { replace: true });
  }, [navigate, returnTo, user]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy('email'); setError(''); setMessage('');
    try {
      const result = await apiClient.post<{ access_token?: string; user?: UserProfile }>(register ? '/auth/register' : '/auth/login', {
        email: email.trim(), password, ...(register ? { full_name: name.trim() } : {}),
      });
      if (result.access_token && result.user) loginWithData(result.access_token, result.user);
      else if (register) { setRegister(false); setPassword(''); setMessage('Đã tạo tài khoản. Bạn có thể đăng nhập.'); }
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(''); }
  };
  const google = async () => {
    setBusy('google'); setError('');
    try {
      const { auth_url } = await apiClient.get<{ auth_url: string }>('/auth/google/start', { params: { return_to: exploreUrl } });
      if (!auth_url || new URL(auth_url).origin !== 'https://accounts.google.com') throw new Error('Không mở được trang đăng nhập Google.');
      window.location.assign(auth_url);
    } catch (failure) { setError((failure as Error).message); setBusy(''); }
  };

  return <AuthFrame title={register ? 'Tạo tài khoản' : 'Đăng nhập'} description="Dùng tài khoản để mua vé và tải thuyết minh cho chuyến đi." back={exploreUrl}>
    <div className="auth-tabs">
      <button type="button" aria-pressed={!register} disabled={!!busy} onClick={() => { setRegister(false); setError(''); }}>Đăng nhập</button>
      <button type="button" aria-pressed={register} disabled={!!busy} onClick={() => { setRegister(true); setError(''); setMessage(''); }}>Tạo tài khoản</button>
    </div>
    <form className="auth-form" onSubmit={submit}>
      {register && <label><span className="field-label">Họ và tên</span><input className="field-input" required autoComplete="name" value={name} onChange={e => setName(e.target.value)} /></label>}
      <label><span className="field-label">Email</span><input type="email" className="field-input" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
      <PasswordField value={password} onChange={setPassword} autoComplete={register ? 'new-password' : 'current-password'} minimum={register ? 6 : undefined} />
      {!register && <Link className="auth-link auth-forgot" to="/forgot-password">Quên mật khẩu?</Link>}
      {error && <p className="auth-error" role="alert">{error}</p>}
      {message && <p className="auth-message" role="status">{message}</p>}
      <Button type="submit" size="lg" loading={busy === 'email'} disabled={!!busy}>
        {register ? 'Tạo tài khoản' : 'Đăng nhập'} <ArrowRight size={17} />
      </Button>
      <Button type="button" size="lg" variant="secondary" loading={busy === 'google'} disabled={!!busy}
        icon={<Globe size={18} />} onClick={() => void google()}>Tiếp tục với Google</Button>
    </form>
    <div className="auth-footer"><Link className="auth-link" to="/admin/login"><Shield size={16} /> Cổng quản trị</Link></div>
  </AuthFrame>;
}
