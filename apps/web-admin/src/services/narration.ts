import { ApiError, apiClient } from './apiClient';
import { apiUrl } from '../config/runtime';
import { prepareAnalytics } from './analytics';

let guestRequest: Promise<unknown> | null = null;
export function ensureGuest() {
  if (!guestRequest) guestRequest = apiClient.post('/guest-sessions').finally(() => { guestRequest = null; });
  return guestRequest;
}

interface Grant {
  playback_id: string;
  grant_token: string;
  stream_url: string;
  lang: string;
}

export async function requestNarration(poiId: string, lang: string, options: {
  tourId?: string; source: 'manual' | 'gps' | 'qr'; consent?: boolean; signedIn: boolean; key: string; signal: AbortSignal;
}) {
  await prepareAnalytics();
  const request = () => apiClient.post<Grant>('/playback-grants', {
    poi_id: poiId, lang, tour_id: options.tourId, trigger_source: options.source,
    consent_trial: options.consent, idempotency_key: options.key,
  }, { signal: options.signal });
  let grant: Grant;
  try { grant = await request(); }
  catch (error) {
    if (options.signedIn || !(error instanceof ApiError) || error.statusCode !== 401 || options.signal.aborted) throw error;
    await ensureGuest();
    grant = await request();
  }
  return { ...grant, stream_url: apiUrl(grant.stream_url) };
}

export async function prepareNarrationLocale(poiId: string, lang: string, signedIn: boolean, signal: AbortSignal) {
  const submit = () => apiClient.post<{ status: 'ready' | 'queued' }>('/localizations/on-demand', { poi_id: poiId, lang }, { signal });
  try {
    return await submit();
  } catch (error) {
    if (signedIn || !(error instanceof ApiError) || error.statusCode !== 401 || signal.aborted) throw error;
    await ensureGuest();
    return submit();
  }
}

export async function prepareNearbyNarrations(poiIds: string[], lang: string, signedIn: boolean, signal: AbortSignal) {
  if (!signedIn) await ensureGuest();
  await apiClient.post('/localizations/prepare-hotset', { poi_ids: poiIds, lang }, { signal });
}
