import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { apiUrl } from '../config/runtime';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  role: 'super_admin' | 'admin' | 'poi_owner' | 'user';
  is_verified: boolean;
  is_poi_owner_verified: boolean;
  avatar_url?: string;
  has_password?: boolean;
  is_google_linked?: boolean;
  permissions: string[];
}

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous' | 'error';

interface AuthContextType {
  status: AuthStatus;
  user: UserProfile | null;
  accessToken: string | null;
  token: string | null; // Backwards-compatible alias for accessToken
  csrfToken: string | null;
  bootstrapError: string | null;
  loginWithData: (token: string, user: UserProfile) => void;
  login: (token: string, user: UserProfile) => void; // Backwards-compatible alias for loginWithData
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
  fetchWithAuth: (url: string, init?: RequestInit) => Promise<Response>;
  hasPermission: (perm: string) => boolean;
  hasRole: (roles: string[]) => boolean;
  retryBootstrap: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// In-flight refresh promise to prevent multiple parallel refresh calls
let activeRefreshPromise: Promise<string | null> | null = null;

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [csrfToken, setCsrfToken] = useState<string | null>(null);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);

  // Keep a ref to the latest accessToken for fetchWithAuth closures
  const tokenRef = useRef<string | null>(null);
  tokenRef.current = accessToken;

  // 1. Fetch CSRF token
  const fetchCsrfToken = useCallback(async (): Promise<string | null> => {
    try {
      const res = await fetch(apiUrl('/auth/csrf'), {
        method: 'GET',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setCsrfToken(data.csrf_token);
        return data.csrf_token;
      }
    } catch (e) {
      console.warn('Could not fetch CSRF token:', e);
    }
    return null;
  }, []);

  // 2. Refresh session with single-flight mutex
  const performRefresh = useCallback(async (): Promise<string | null> => {
    if (activeRefreshPromise) {
      return activeRefreshPromise;
    }

    activeRefreshPromise = (async () => {
      try {
        const res = await fetch(apiUrl('/auth/refresh'), {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!res.ok) {
          setAccessToken(null);
          setUser(null);
          return null;
        }

        const data = await res.json();
        const newToken = data.access_token;
        setAccessToken(newToken);
        tokenRef.current = newToken;

        // Also fetch user profile /me
        const meRes = await fetch(apiUrl('/auth/me'), {
          headers: {
            Authorization: `Bearer ${newToken}`,
          },
          credentials: 'include',
        });

        if (meRes.ok) {
          const profile = await meRes.json();
          setUser(profile);
          setStatus('authenticated');
        } else {
          setUser(null);
          setStatus('anonymous');
        }

        return newToken;
      } catch (err: any) {
        // Distinguish network error from auth rejection
        console.error('Session refresh error:', err);
        throw err;
      } finally {
        activeRefreshPromise = null;
      }
    })();

    return activeRefreshPromise;
  }, []);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const token = await performRefresh();
      return !!token;
    } catch {
      return false;
    }
  }, [performRefresh]);

  // 3. Bootstrap authentication on load
  const bootstrapAuth = useCallback(async () => {
    setStatus('loading');
    setBootstrapError(null);
    try {
      await fetchCsrfToken();
      const token = await performRefresh();
      if (token) {
        setStatus('authenticated');
      } else {
        setStatus('anonymous');
      }
    } catch (err: any) {
      // Network error occurred
      setBootstrapError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.');
      setStatus('error');
    }
  }, [fetchCsrfToken, performRefresh]);

  useEffect(() => {
    bootstrapAuth();
  }, [bootstrapAuth]);

  // 4. Login helper
  const loginWithData = useCallback((token: string, userProfile: UserProfile) => {
    setAccessToken(token);
    tokenRef.current = token;
    setUser(userProfile);
    setStatus('authenticated');
  }, []);

  // 5. Logout helper
  const logout = useCallback(async () => {
    try {
      await fetch(apiUrl('/auth/logout'), {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      console.warn('Logout request failed:', e);
    } finally {
      setAccessToken(null);
      tokenRef.current = null;
      setUser(null);
      setStatus('anonymous');
    }
  }, []);

  // 6. Logout all devices
  const logoutAll = useCallback(async () => {
    try {
      if (tokenRef.current) {
        await fetch(apiUrl('/auth/logout-all'), {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${tokenRef.current}`,
          },
          credentials: 'include',
        });
      }
    } catch (e) {
      console.warn('Logout all failed:', e);
    } finally {
      setAccessToken(null);
      tokenRef.current = null;
      setUser(null);
      setStatus('anonymous');
    }
  }, []);

  // 7. Authenticated Fetch wrapper with automatic 401 retry
  const fetchWithAuth = useCallback(
    async (url: string, init: RequestInit = {}): Promise<Response> => {
      const targetUrl = apiUrl(url);
      const headers = new Headers(init.headers || {});
      if (tokenRef.current) {
        headers.set('Authorization', `Bearer ${tokenRef.current}`);
      }
      if (csrfToken && !headers.has('X-CSRF-Token')) {
        headers.set('X-CSRF-Token', csrfToken);
      }

      let res = await fetch(targetUrl, {
        ...init,
        headers,
        credentials: 'include',
      });

      // If 401, attempt silent refresh once
      if (res.status === 401) {
        try {
          const newToken = await performRefresh();
          if (newToken) {
            headers.set('Authorization', `Bearer ${newToken}`);
            res = await fetch(targetUrl, {
              ...init,
              headers,
              credentials: 'include',
            });
          } else {
            setStatus('anonymous');
          }
        } catch {
          // Keep response as 401 if refresh failed
        }
      }

      return res;
    },
    [csrfToken, performRefresh]
  );

  const hasPermission = useCallback(
    (perm: string) => {
      if (!user) return false;
      if (user.role === 'super_admin') return true;
      return user.permissions?.includes(perm) || false;
    },
    [user]
  );

  const hasRole = useCallback(
    (roles: string[]) => {
      if (!user) return false;
      return roles.includes(user.role);
    },
    [user]
  );

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        accessToken,
        token: accessToken,
        csrfToken,
        bootstrapError,
        loginWithData,
        login: loginWithData,
        logout,
        logoutAll,
        refreshSession,
        fetchWithAuth,
        hasPermission,
        hasRole,
        retryBootstrap: bootstrapAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
