import { useState, type FormEvent } from 'react';
import { AuthFrame } from '../components/AuthFrame';
import { Button } from '../components/ui';
import { apiClient } from '../services/apiClient';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const send = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setError('');
    try { await apiClient.post('/auth/forgot-password', { email: email.trim() }); setSent(true); }
    catch (failure) { setError((failure as Error).message); }
    finally { setBusy(false); }
  };
  return <AuthFrame title="Khôi phục mật khẩu" description="Nhập email dùng để đăng nhập TourVoice." back="/client/login" backLabel="Về đăng nhập">
    {sent ? <p className="auth-message" role="status">Nếu email có tài khoản dùng mật khẩu, bạn sẽ nhận được hướng dẫn khôi phục.</p>
      : <form className="auth-form" onSubmit={send}>
        <label><span className="field-label">Email</span><input type="email" className="field-input" required autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <Button type="submit" size="lg" loading={busy}>Gửi liên kết khôi phục</Button>
      </form>}
  </AuthFrame>;
}
