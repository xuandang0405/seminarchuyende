import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export const AuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refreshSession, user } = useAuth();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('Đang hoàn tất đăng nhập...');

  useEffect(() => {
    const errorParam = searchParams.get('error');
    const linkedParam = searchParams.get('linked');
    const returnTo = searchParams.get('return_to') || '/';

    if (errorParam) {
      setErrorMsg(decodeURIComponent(errorParam));
      return;
    }

    if (linkedParam === 'true') {
      setStatusMsg('Liên kết Google thành công! Đang chuyển hướng...');
      setTimeout(() => {
        navigate(returnTo || '/account/security', { replace: true });
      }, 1500);
      return;
    }

    // Standard Google login flow:
    // Backend has set the HttpOnly cookie. Web client now refreshes session into memory.
    const completeAuth = async () => {
      try {
        const ok = await refreshSession();
        if (!ok) {
          setErrorMsg('Không thể khôi phục phiên đăng nhập từ máy chủ. Vui lòng thử lại.');
          return;
        }

        setStatusMsg('Xác thực thành công! Đang chuyển hướng...');
        setTimeout(() => {
          // Google login users are strictly directed to /client portal
          const target = (!returnTo || returnTo === '/' || returnTo === '/login' || returnTo.startsWith('/admin')) ? '/client' : returnTo;
          navigate(target, { replace: true });
        }, 800);
      } catch (err: any) {
        setErrorMsg(err.message || 'Lỗi xử lý phiên đăng nhập.');
      }
    };

    completeAuth();
  }, [searchParams, refreshSession, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4 font-['Plus_Jakarta_Sans',sans-serif]">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl text-center space-y-6">
        {errorMsg ? (
          <>
            <div className="w-14 h-14 rounded-2xl bg-red-500/20 text-red-400 flex items-center justify-center mx-auto">
              <AlertCircle className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Đăng Nhập Thất Bại</h2>
              <p className="text-sm text-slate-300">{errorMsg}</p>
            </div>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-colors shadow-lg shadow-indigo-600/30 text-sm"
            >
              Quay lại trang Đăng nhập
            </button>
          </>
        ) : (
          <>
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Đang Xử Lý Xác Thực</h2>
              <p className="text-sm text-slate-400">{statusMsg}</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
