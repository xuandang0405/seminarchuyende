import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AuthFrame } from '../components/AuthFrame';
import { useAuth } from '../context/AuthContext';

export function AuthCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const [error, setError] = useState(params.get('error') || '');
  const linked = params.get('linked') === 'true';
  const requested = params.get('return_to') || '';
  const safe = requested.startsWith('/') && !requested.startsWith('//') && !requested.includes('\\');
  const target = linked
    ? safe && requested.startsWith('/account') ? requested : '/account/security'
    : safe && (requested === '/client' || requested.startsWith('/client?') || requested.startsWith('/client/')) ? requested : '/client';
  useEffect(() => {
    if (params.get('error')) return;
    if (linked) { navigate(target, { replace: true }); return; }
    let active = true;
    void refreshSession().then(ok => {
      if (!active) return;
      if (ok) navigate(target, { replace: true });
      else setError('Chưa khôi phục được phiên. Hãy đăng nhập lại.');
    }).catch(() => { if (active) setError('Chưa kết nối được máy chủ. Hãy thử lại.'); });
    return () => { active = false; };
  }, [linked, params, target, refreshSession, navigate]);
  return <AuthFrame title={error ? 'Chưa đăng nhập được' : 'Đang xác thực'} back="/client/login" backLabel="Về đăng nhập">
    {error ? <p className="auth-error" role="alert">{error}</p> : <p className="auth-message" role="status">Đang hoàn tất phiên đăng nhập.</p>}
  </AuthFrame>;
}
