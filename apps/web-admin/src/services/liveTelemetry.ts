import { useEffect } from 'react';
import { apiUrl } from '../config/runtime';

export function newRequestId() {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
}

function sendRuntime(path: 'presence' | 'listen', body: object) {
  return fetch(apiUrl('/analytics/runtime/' + path), {
    method: 'POST',
    credentials: 'omit',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    keepalive: true,
  }).catch(() => {});
}

export function useWebPresence() {
  useEffect(() => {
    const leaseId = newRequestId();
    let present = true;
    let pending = false;
    const close = () => {
      present = false;
      void sendRuntime('presence', { lease_id: leaseId, active: false });
    };
    const heartbeat = async () => {
      if (!present || pending || !navigator.onLine) return;
      pending = true;
      await sendRuntime('presence', { lease_id: leaseId, active: true });
      pending = false;
      if (!present) close();
    };
    const enter = () => { present = true; void heartbeat(); };
    const refreshVisible = () => { if (!document.hidden) void heartbeat(); };
    const first = window.setTimeout(heartbeat, 0);
    const timer = window.setInterval(heartbeat, 15000);
    window.addEventListener('online', heartbeat);
    window.addEventListener('pagehide', close);
    window.addEventListener('pageshow', enter);
    document.addEventListener('visibilitychange', refreshVisible);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
      window.removeEventListener('online', heartbeat);
      window.removeEventListener('pagehide', close);
      window.removeEventListener('pageshow', enter);
      document.removeEventListener('visibilitychange', refreshVisible);
      close();
    };
  }, []);
}

export function reportWebListen(grantToken: string, listenedMs: number, completed = false) {
  return sendRuntime('listen', { grant_token: grantToken, listened_ms: listenedMs, completed });
}
