import { apiClient, getStoredToken } from './apiClient';
import { apiUrl } from '../config/runtime';

const bytes = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const sha = async (buffer: BufferSource) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)))
  .map(v => v.toString(16).padStart(2, '0')).join('');
const db = () => new Promise<IDBDatabase>((resolve, reject) => {
  const request = indexedDB.open('tourvoice-offline', 1);
  request.onupgradeneeded = () => request.result.createObjectStore('packs');
  request.onsuccess = () => resolve(request.result);
  request.onerror = () => reject(request.error);
});
async function storage(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest) {
  const database = await db();
  try {
    return await new Promise<any>((resolve, reject) => {
      const tx = database.transaction('packs', mode);
      const request = run(tx.objectStore('packs'));
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error || new Error('Không lưu được gói ngoại tuyến.'));
    });
  } finally { database.close(); }
}
async function verify(pack: any, userId: string, lang: string) {
  const key = import.meta.env.VITE_LICENSE_PUBLIC_KEY || localStorage.getItem('tourvoice_license_key');
  if (!key || !pack?.license?.signed_payload) throw new Error('Thiếu khóa xác minh.');
  const publicKey = await crypto.subtle.importKey('raw', bytes(key), { name: 'Ed25519' }, false, ['verify']);
  if (!await crypto.subtle.verify('Ed25519', publicKey, bytes(pack.license.license_signature),
    new TextEncoder().encode(pack.license.signed_payload))) throw new Error('Giấy phép không hợp lệ.');
  const payload = JSON.parse(pack.license.signed_payload);
  const lastSeen = Number(localStorage.getItem('tourvoice_offline_last_seen') || 0);
  if (payload.user_id !== userId || Date.parse(payload.expires_at) <= Date.now() ||
    Date.parse(payload.issued_at) > Date.now() + 300000 || Date.now() + 300000 < lastSeen ||
    await sha(new TextEncoder().encode(pack.manifest_json)) !== payload.manifest_sha256) {
    throw new Error('Gói đã hết hạn hoặc không toàn vẹn. Kết nối mạng để tải lại.');
  }
  const manifest = JSON.parse(pack.manifest_json);
  if (manifest.package_id !== payload.package_id || manifest.tour_id !== payload.tour_id || manifest.language_code !== lang) {
    throw new Error('Sai gói hoặc ngôn ngữ.');
  }
  localStorage.setItem('tourvoice_offline_last_seen', String(Math.max(Date.now(), lastSeen)));
  return manifest;
}
export async function downloadOfflineTour(tourId: string, userId: string, lang: string, progress: (value: string) => void, signal?: AbortSignal) {
  const pack = await apiClient.post(`/tours/${encodeURIComponent(tourId)}/offline-pack?language_code=${lang}`, undefined, { signal });
  const pinned = import.meta.env.VITE_LICENSE_PUBLIC_KEY || localStorage.getItem('tourvoice_license_key');
  if (pinned && pinned !== pack.license.public_key) throw new Error('Khóa xác minh đã thay đổi.');
  if (!pinned) {
    if (!window.isSecureContext) throw new Error('Cần HTTPS để tải ngoại tuyến.');
    localStorage.setItem('tourvoice_license_key', pack.license.public_key);
  }
  const manifest = await verify(pack, userId, lang);
  if (manifest.tour_id !== tourId) throw new Error('Gói ngoại tuyến không thuộc tuyến đã chọn.');
  if (manifest.total_bytes > 300 * 1024 * 1024) throw new Error('Gói vượt giới hạn 300 MB.');
  const capacity = await navigator.storage?.estimate();
  if (capacity?.quota && manifest.total_bytes > capacity.quota - (capacity.usage || 0)) throw new Error('Không đủ dung lượng.');
  const files: Record<string, Blob> = {};
  for (const [i, asset] of manifest.files.entries()) {
    const token = getStoredToken();
    const response = await fetch(apiUrl(asset.download_url), { credentials: 'include', signal,
      headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!response.ok) throw new Error('Tải file thất bại. Gói cũ vẫn được giữ.');
    const blob = await response.blob();
    if (blob.size !== asset.file_size_bytes || await sha(await blob.arrayBuffer()) !== asset.sha256) throw new Error('File sai checksum.');
    files[asset.asset_id] = blob;
    progress(`Đang tải ${i + 1}/${manifest.files.length}`);
  }
  // Atomic commit after verification; failed downloads never overwrite the current pack.
  signal?.throwIfAborted();
  await storage('readwrite', store => store.put({ manifest_json: pack.manifest_json, license: pack.license, files }, `${userId}:${lang}:${tourId}`));
  await navigator.storage?.persist?.().catch(() => false);
  progress('Đã lưu thuyết minh ngoại tuyến (7 ngày).');
}
export async function removeOfflineTour(userId: string, lang: string, tourId: string) {
  const prefix = `${userId}:${lang}`;
  const legacy = await storage('readonly', store => store.get(prefix));
  if (legacy && JSON.parse(legacy.manifest_json).tour_id === tourId) {
    await storage('readwrite', store => store.delete(prefix));
  }
  await storage('readwrite', store => store.delete(`${prefix}:${tourId}`));
}
async function verifiedPacks(userId: string | undefined, lang: string) {
  if (!userId) return [];
  try {
    const prefix = `${userId}:${lang}`;
    const records = await storage('readonly', store => store.getAll(IDBKeyRange.bound(prefix, prefix + ':\uffff')));
    const packs = new Map<string, any>();
    for (const pack of records) {
      try {
        const manifest = await verify(pack, userId, lang);
        packs.set(manifest.tour_id, { ...manifest, tour_name: manifest.tour_name || manifest.tour_code || 'Tuyến đã lưu', blobs: pack.files });
      } catch { /* Expired, invalid or older keys are skipped. */ }
    }
    return [...packs.values()];
  } catch { return []; }
}
export async function getOfflineTours(userId: string | undefined, lang: string) {
  return (await verifiedPacks(userId, lang)).map(({ tour_id, tour_name, pois, total_bytes }) => ({ tour_id, tour_name, pois, total_bytes }));
}
export async function getOfflineAudio(userId: string | undefined, lang: string, poiId: string, tourId?: string) {
  for (const pack of await verifiedPacks(userId, lang)) {
    if (tourId && pack.tour_id !== tourId) continue;
    const poi = pack.pois.find((p: any) => (p.id || p._id) === poiId);
    const asset = pack.audio_assets?.find((a: any) => a.asset_id === poi?.audio_asset_id);
    const blob = asset && pack.blobs[asset.asset_id];
    if (blob && await sha(await blob.arrayBuffer()) === asset.sha256) {
      return { url: URL.createObjectURL(blob), lang: poi.resolved_lang || lang };
    }
  }
  return null;
}
