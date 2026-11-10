import React, { useEffect, useState } from 'react';
import { ApiError, apiClient } from './apiClient';
import { newRequestId } from './liveTelemetry';

const CONSENT = 'tourvoice_analytics_consent';
const OUTBOX = 'tourvoice_analytics_outbox';
const CONSENT_CHANGED = 'tourvoice-analytics-consent-changed';
let deviceReady: Promise<any> | null = null;
let syncing = false;
let consentUpdates = Promise.resolve();
let syncedConsent: boolean | undefined;
async function device() {
  if (!deviceReady) deviceReady = apiClient.post('/device/bootstrap', { platform: 'web' })
    .catch(error => { deviceReady = null; throw error; });
  return deviceReady;
}
function syncConsent() {
  const update = consentUpdates.catch(() => {}).then(async () => {
    const enabled = localStorage.getItem(CONSENT) === 'true';
    if (enabled === syncedConsent) return;
    const info = await device();
    await apiClient.post('/analytics/consent', { device_id: info.device_id, consent_granted: enabled, scopes: ['events'] });
    syncedConsent = enabled;
  });
  consentUpdates = update;
  return update;
}
export async function flushAnalytics() {
  if (syncing || localStorage.getItem(CONSENT) !== 'true' || !navigator.onLine || !localStorage.getItem(OUTBOX)) return;
  syncing = true;
  try {
    await syncConsent();
    while (localStorage.getItem(CONSENT) === 'true') {
      const events = JSON.parse(localStorage.getItem(OUTBOX) || '[]').slice(0, 20);
      if (!events.length) break;
      const result = await apiClient.post('/analytics/events/batch', { events });
      const acknowledged = new Set((result.acks || []).filter((a: any) =>
        ['accepted', 'duplicate', 'rejected_permanent'].includes(a.status)).map((a: any) => a.event_id));
      if (localStorage.getItem(CONSENT) !== 'true') break;
      const latest = JSON.parse(localStorage.getItem(OUTBOX) || '[]');
      localStorage.setItem(OUTBOX, JSON.stringify(latest.filter((e: any) => !acknowledged.has(e.event_id))));
      if (acknowledged.size < events.length) break;
    }
  } catch { /* Preserve unacknowledged events for reconnect. */ }
  finally { syncing = false; }
}
export async function prepareAnalytics() {
  if (localStorage.getItem(CONSENT) === 'true') {
    try { await syncConsent(); } catch { /* Listening remains available. */ }
  }
}
export function useVisitorAnalytics(lang: string) {
  useEffect(() => {
    let sessionId: string | undefined;
    let pending = false;
    const heartbeat = async () => {
      if (pending || !navigator.onLine || localStorage.getItem(CONSENT) !== 'true') return;
      pending = true;
      try {
        await syncConsent();
        if (localStorage.getItem(CONSENT) !== 'true') return;
        if (sessionId) {
          await apiClient.post('/visitor-sessions/' + sessionId + '/heartbeat');
        } else {
          const session = await apiClient.post<{ _id: string }>('/visitor-sessions/start-or-resume', {
            platform: 'web', locale: lang,
          });
          sessionId = session._id;
        }
      } catch (error) {
        sessionId = undefined;
        if (error instanceof ApiError && [401, 403].includes(error.statusCode)) {
          deviceReady = null;
          syncedConsent = undefined;
        }
      } finally { pending = false; }
    };
    const connected = () => { void heartbeat(); void flushAnalytics(); };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== CONSENT) return;
      syncedConsent = undefined;
      sessionId = undefined;
      connected();
    };
    connected();
    const presenceTimer = window.setInterval(heartbeat, 20000);
    const flushTimer = window.setInterval(flushAnalytics, 4000);
    window.addEventListener('online', connected);
    window.addEventListener(CONSENT_CHANGED, connected);
    window.addEventListener('storage', onStorage);
    return () => {
      window.clearInterval(presenceTimer);
      window.clearInterval(flushTimer);
      window.removeEventListener('online', connected);
      window.removeEventListener(CONSENT_CHANGED, connected);
      window.removeEventListener('storage', onStorage);
    };
  }, [lang]);
}
function enqueue(event: { event_type: string; poi_id?: string; tour_id?: string; playback_id?: string;
  locale: string; source?: string; properties?: object }) {
  try {
    if (localStorage.getItem(CONSENT) !== 'true') return false;
    const queue = JSON.parse(localStorage.getItem(OUTBOX) || '[]');
    queue.push({ ...event, event_id: newRequestId(), client_occurred_at: new Date().toISOString() });
    localStorage.setItem(OUTBOX, JSON.stringify(queue.slice(-200)));
    void flushAnalytics();
    return true;
  } catch { return false; }
}
export function trackNarration(type: string, poiId: string, playbackId: string, locale: string, deltaMs?: number) {
  enqueue({ event_type: type, poi_id: poiId, playback_id: playbackId, locale,
    properties: deltaMs ? { delta_ms: deltaMs } : {} });
}
export function trackQrScan(locale: string, target: { poi_id?: string; tour_id?: string }) {
  return enqueue({ event_type: 'qr_scanned', source: 'qr', locale, ...target });
}
export function AnalyticsConsent() {
  const [choice, setChoice] = useState(localStorage.getItem(CONSENT));
  const choose = async (enabled: boolean) => {
    localStorage.setItem(CONSENT, String(enabled));
    setChoice(String(enabled));
    if (!enabled) localStorage.removeItem(OUTBOX);
    try { await syncConsent(); } catch { /* Local choice remains effective offline. */ }
    window.dispatchEvent(new Event(CONSENT_CHANGED));
  };
  return <div className="tv-privacy">
    <p>Thống kê lượt nghe bằng mã thiết bị · {choice === 'true' ? 'Đang bật' : 'Đang tắt'}</p>
    <button type="button" className="tv-link" onClick={() => choose(choice !== 'true')}>
      {choice === 'true' ? 'Tắt thống kê' : 'Bật thống kê'}
    </button>
  </div>;
}
