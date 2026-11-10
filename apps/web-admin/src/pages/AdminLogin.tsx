import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { AuthFrame, PasswordField } from '../components/AuthFrame';
import { Button } from '../components/ui';
import { useAuth, type UserProfile } from '../context/AuthContext';
import { apiClient } from '../services/apiClient';

export function AdminLogin() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loginWithData, logout } = useAuth();
  const requested = location.state?.from?.pathname as string | undefined;
  const target = requested?.startsWith('/') && !requested.startsWith('//') &&
    !['/admin/login', '/login', '/'].includes(requested) ? requested : user?.role === 'poi_owner' ? '/owner' : '/admin';
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [business, setBusiness] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (user && user.role !== 'user') {
      navigate(user.role === 'poi_owner' && !user.is_poi_owner_verified ? '/owner/registration-status' : target, { replace: true });
    }
  }, [navigate, target, user]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setError(''); setMessage('');
    try {
      const result = await apiClient.post<{ access_token: string; user: UserProfile }>(register ? '/auth/register-owner' : '/auth/admin/login', {
        email: email.trim(), password, ...(register ? { full_name: name.trim(), business_name: business.trim() } : {}),
      });
      if (register) {
        setRegister(false); setPassword(''); setMessage('Đã gửi hồ sơ cơ sở. Bạn có thể đăng nhập để theo dõi xét duyệt.');
      } else loginWithData(result.access_token, result.user);
    } catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  };

  return <AuthFrame title={register ? 'Đăng ký cơ sở' : 'Đăng nhập quản trị'} console
    description={register ? 'Gửi hồ sơ để quản lý thông tin địa điểm của bạn.' : 'Dành cho quản trị viên và chủ cơ sở.'}>
    {user?.role === 'user' ? <div className="auth-form">
      <p className="auth-message">Bạn đang dùng tài khoản du khách {user.email}.</p>
      <Button type="button" onClick={() => void logout()}>Đăng xuất để đổi tài khoản</Button>
    </div> : <>
      <div className="auth-tabs">
        <button type="button" aria-pressed={!register} disabled={busy} onClick={() => { setRegister(false); setError(''); }}>Đăng nhập</button>
        <button type="button" aria-pressed={register} disabled={busy} onClick={() => { setRegister(true); setError(''); setMessage(''); }}>Đăng ký cơ sở</button>
      </div>
      <form className="auth-form" onSubmit={submit}>
        {register && <>
          <label><span className="field-label">Họ và tên</span><input className="field-input" required autoComplete="name" value={name} onChange={e => setName(e.target.value)} /></label>
          <label><span className="field-label">Tên cơ sở</span><input className="field-input" required autoComplete="organization" value={business} onChange={e => setBusiness(e.target.value)} /></label>
        </>}
        <label><span className="field-label">Email</span><input className="field-input" type="email" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
        <PasswordField value={password} onChange={setPassword} autoComplete={register ? 'new-password' : 'current-password'} minimum={register ? 6 : undefined} />
        {!register && <Link className="auth-link auth-forgot" to="/forgot-password">Quên mật khẩu?</Link>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="auth-message" role="status">{message}</p>}
        <Button type="submit" size="lg" loading={busy}>{register ? 'Gửi hồ sơ' : 'Đăng nhập quản trị'} <ArrowRight size={17} /></Button>
      </form>
    </>}
  </AuthFrame>;
}
