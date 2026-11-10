import { useEffect, useRef } from 'react';

/** Refresh visible consoles without overlapping background requests. */
export function useLiveRefresh(refresh: () => Promise<unknown>, enabled = true) {
  const latest = useRef(refresh);
  latest.current = refresh;
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let pending = false;
    const run = async () => {
      if (!active || pending || document.hidden || !navigator.onLine) return;
      pending = true;
      try { await latest.current(); } catch { /* Screen owns its error feedback. */ }
      finally { pending = false; }
    };
    const timer = window.setInterval(run, 3000);
    window.addEventListener('online', run);
    document.addEventListener('visibilitychange', run);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener('online', run);
      document.removeEventListener('visibilitychange', run);
    };
  }, [enabled]);
}
