import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AuthFrame, PasswordField } from '../components/AuthFrame';
import { Button } from '../components/ui';
import { apiClient } from '../services/apiClient';

export function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const reset = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || password !== confirmation) { setError('Hai mật khẩu chưa khớp.'); return; }
    setBusy(true); setError('');
    try { await apiClient.post('/auth/reset-password', { token, new_password: password }); setDone(true); }
    catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  };
  return <AuthFrame title="Đặt lại mật khẩu" description="Chọn mật khẩu mới có ít nhất 6 ký tự." back="/client/login" backLabel="Về đăng nhập">
    {!token ? <p className="auth-error">Mở liên kết khôi phục trong email để tiếp tục.</p>
      : done ? <div className="auth-form"><p className="auth-message" role="status">Đã lưu mật khẩu mới.</p><Link className="app-button" data-variant="primary" to="/client/login">Đăng nhập</Link></div>
        : <form className="auth-form" onSubmit={reset}>
          <PasswordField value={password} onChange={setPassword} minimum={6} autoComplete="new-password" />
          <label><span className="field-label">Nhập lại mật khẩu</span><input type="password" className="field-input" required autoComplete="new-password" value={confirmation} onChange={e => setConfirmation(e.target.value)} /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <Button type="submit" size="lg" loading={busy}>Lưu mật khẩu</Button>
        </form>}
  </AuthFrame>;
}
