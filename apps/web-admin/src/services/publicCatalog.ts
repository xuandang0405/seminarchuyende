import { useEffect, useState } from 'react';
import { apiClient } from './apiClient';
import { apiUrl } from '../config/runtime';
import { placeId, type Place } from '../pages/TouristLeaflet';

export type Tour = Place & {
  poi_count?: number; stops?: { poi_id: string; stop_order?: number }[]; poi_ids?: string[]; pois?: Place[];
  price_amount?: number; is_paid?: boolean; is_purchasable?: boolean;
  localizations?: Record<string, { name?: string; title?: string; description?: string }>;
};
type Snapshot = {
  lang: string; places: Place[]; tours: Tour[]; cursor?: string; etag?: string;
};
type Delta = {
  sync_cursor: string; sync_mode: 'full' | 'delta'; items: Place[];
  removed_poi_ids: string[]; ordered_poi_ids: string[];
};
type State = { snapshot?: Snapshot; loading: boolean; failed: boolean; cached: boolean; requestLang: string };

async function catalogStorage<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>) {
  const db = await new Promise<IDBDatabase>((resolve, reject) => {
    const open = indexedDB.open('tourvoice-public-catalog', 1);
    open.onupgradeneeded = () => open.result.createObjectStore('locales');
    open.onsuccess = () => resolve(open.result);
    open.onerror = () => reject(open.error);
  });
  try {
    return await new Promise<T>((resolve, reject) => {
      const transaction = db.transaction('locales', mode);
      const request = action(transaction.objectStore('locales'));
      transaction.oncomplete = () => resolve(request.result);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally { db.close(); }
}

async function loadPlaces(lang: string, old: Snapshot | undefined, signal: AbortSignal) {
  const query = new URLSearchParams({ lang });
  if (old?.cursor) query.set('updated_after', old.cursor);
  const headers = new Headers({ Accept: 'application/json' });
  if (old?.etag) headers.set('If-None-Match', old.etag);
  const response = await fetch(apiUrl('/poi/load-all?' + query), { headers, signal, cache: 'no-store' });
  if (response.status === 304 && old) return { places: old.places, cursor: old.cursor, etag: old.etag };
  if (response.status === 404) {
    // Support web-only deploys during a rolling upgrade of the API.
    const places = await readPages(skip => apiClient.get<{ items: Place[] }>('/pois', {
      params: { lang, skip, limit: 100 }, signal,
    }).then(page => page.items));
    return { places };
  }
  if (!response.ok) throw new Error('Chưa đồng bộ được điểm dừng.');
  const delta: Delta = await response.json();
  const etag = response.headers.get('etag') || undefined;
  if (delta.sync_mode === 'full') return { places: delta.items, cursor: delta.sync_cursor, etag };
  const byId = new Map(old?.places.map(item => [placeId(item), item]));
  for (const id of delta.removed_poi_ids) byId.delete(id);
  for (const item of delta.items) byId.set(placeId(item), item);
  const places = delta.ordered_poi_ids.map(id => byId.get(id));
  if (places.some(item => !item)) return loadPlaces(lang, undefined, signal);
  return { places: places as Place[], cursor: delta.sync_cursor, etag };
}

async function readPages<T>(read: (skip: number) => Promise<T[]>) {
  const items: T[] = [];
  for (let skip = 0; ; skip += 100) {
    const page = await read(skip);
    items.push(...page);
    if (page.length < 100) return items;
  }
}

const emptyPlaces: Place[] = [];
const emptyTours: Tour[] = [];

export function usePublicCatalog(lang: string, online: boolean, revision: number) {
  const [state, setState] = useState<State>({ loading: true, failed: false, cached: false, requestLang: lang });
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort('timeout'), 10_000);
    const signal = controller.signal;
    let disposed = false;
    const read = async (locale: string) => catalogStorage<Snapshot | undefined>('readonly', store => store.get(locale)).catch(() => undefined);
    async function sync() {
      const target = await read(lang);
      let cached = target;
      for (const fallback of ['en', 'vi']) {
        if (cached) break;
        if (fallback !== lang) cached = await read(fallback);
      }
      if (disposed) return;
      setState({ snapshot: cached, loading: online, cached: Boolean(cached), failed: false, requestLang: lang });
      if (!online) return;
      const [pois, tours] = await Promise.allSettled([
        loadPlaces(lang, target, signal),
        readPages(skip => apiClient.get<Tour[]>('/tours', { params: { lang, skip, limit: 100 }, signal, token: null })),
      ]);
      if (disposed) return;
      if (pois.status !== 'fulfilled') {
        setState({ snapshot: cached, loading: false, cached: Boolean(cached), failed: true, requestLang: lang });
        return;
      }
      const snapshot: Snapshot = { lang, ...pois.value, tours: tours.status === 'fulfilled' ? tours.value : target?.tours || [] };
      setState({ snapshot, loading: false, cached: false, failed: tours.status !== 'fulfilled', requestLang: lang });
      await catalogStorage('readwrite', store => store.put(snapshot, lang)).catch(() => {});
    }
    void sync().finally(() => window.clearTimeout(timeout));
    return () => { disposed = true; controller.abort(); window.clearTimeout(timeout); };
  }, [lang, online, revision]);
  const current = state.requestLang === lang ? state : undefined;
  return {
    places: current?.snapshot?.places || emptyPlaces,
    tours: current?.snapshot?.tours || emptyTours,
    loading: current?.loading ?? true,
    cached: current?.cached ?? false,
    failed: current?.failed ?? false,
    contentLang: current?.snapshot?.lang,
  };
}
