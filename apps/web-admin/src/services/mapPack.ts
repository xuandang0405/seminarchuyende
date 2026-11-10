import { useEffect, useState } from 'react';
import { apiClient } from './apiClient';

export type MapMode = 'cloud' | 'offline' | 'hybrid';
export type MapManifest = {
  scope: 'district-4';
  label: string;
  version: string;
  source_date: string;
  bbox: [number, number, number, number];
  archive: string;
  size: number;
  sha256: string;
};
export type ActiveMapPack = { manifest: MapManifest; blob: Blob };

const manifestPath = '/static/maps/packs/current/manifest.json';
const cacheName = 'tourvoice-verified-map-packs-v1';
const activePath = '/static/maps/active/district-4';

function checkManifest(data: MapManifest): MapManifest {
  if (data?.scope !== 'district-4' || !/^q4-\d{8}$/.test(data.version) ||
    data.archive !== `/static/maps/packs/${data.version}/district-4.pmtiles` ||
    !/^[a-f0-9]{64}$/.test(data.sha256) || !Number.isInteger(data.size) || data.size < 127 || data.size > 50_000_000 ||
    !Array.isArray(data.bbox) || data.bbox.length !== 4 || !data.bbox.every(Number.isFinite) ||
    data.bbox[0] >= data.bbox[2] || data.bbox[1] >= data.bbox[3]) {
    throw new Error('Thông tin gói bản đồ không hợp lệ.');
  }
  return data;
}

async function readManifest(signal: AbortSignal) {
  const response = await fetch(manifestPath, { cache: 'no-cache', signal });
  if (response.ok && response.headers.get('content-type')?.includes('json')) {
    return checkManifest(await response.json());
  }
  return checkManifest(await apiClient.get<MapManifest>('/maps/offline-manifest', { signal }));
}

async function verifyArchive(manifest: MapManifest, blob: Blob) {
  if (blob.size !== manifest.size) throw new Error('Kích thước gói bản đồ không khớp.');
  const hash = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
  const digest = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  if (digest !== manifest.sha256) throw new Error('Gói bản đồ chưa qua kiểm tra toàn vẹn.');
}

async function readActivePack(): Promise<ActiveMapPack | null> {
  if (!window.caches || !crypto.subtle) return null;
  const record = await caches.match(activePath, { cacheName });
  if (!record) return null;
  const manifest = checkManifest(JSON.parse(decodeURIComponent(record.headers.get('x-map-manifest') || 'null')));
  const blob = await record.blob();
  await verifyArchive(manifest, blob);
  return { manifest, blob };
}

export function useMapPack(online: boolean) {
  const [mode, setMode] = useState<MapMode>(() => {
    const saved = localStorage.getItem('tourvoice_map_mode');
    return saved === 'cloud' || saved === 'offline' ? saved : 'hybrid';
  });
  const [manifest, setManifest] = useState<MapManifest | null>(null);
  const [installed, setInstalled] = useState<ActiveMapPack | null>(null);
  const [busy, setBusy] = useState(false);
  const [repairRequired, setRepairRequired] = useState(false);
  const [message, setMessage] = useState('');
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let disposed = false;
    readActivePack().then(value => { if (!disposed) setInstalled(value); })
      .catch(() => { if (!disposed) setRepairRequired(true); })
      .finally(() => { if (!disposed) setChecked(true); });
    return () => { disposed = true; };
  }, []);
  useEffect(() => {
    if (!online) return;
    const controller = new AbortController();
    const deadline = window.setTimeout(() => controller.abort(), 5000);
    readManifest(controller.signal).then(value => {
      if (!controller.signal.aborted) setManifest(value);
    }).catch(() => {}).finally(() => window.clearTimeout(deadline));
    return () => { window.clearTimeout(deadline); controller.abort(); };
  }, [online]);

  const changeMode = (next: MapMode) => {
    setMode(next);
    localStorage.setItem('tourvoice_map_mode', next);
  };
  const install = async () => {
    if (!online || busy) return;
    setBusy(true);
    setMessage('Đang tải và kiểm tra gói bản đồ…');
    try {
      if (!window.caches || !crypto.subtle) throw new Error('Cần HTTPS hoặc localhost để lưu bản đồ.');
      const signal = AbortSignal.timeout(30_000);
      const next = await readManifest(signal);
      const response = await fetch(next.archive, { signal, cache: 'no-store' });
      if (!response.ok) throw new Error('Chưa tải được tệp bản đồ.');
      const blob = await response.blob();
      await verifyArchive(next, blob);
      const cache = await caches.open(cacheName);
      // Replacing one Cache entry commits the manifest and verified bytes together.
      await cache.put(activePath, new Response(blob, { headers: {
        'Content-Type': 'application/octet-stream',
        'X-Map-Manifest': encodeURIComponent(JSON.stringify(next)),
      } }));
      setManifest(next);
      setInstalled({ manifest: next, blob });
      setRepairRequired(false);
      changeMode('offline');
      setMessage('Đã lưu bản đồ Quận 4.');
    } catch (error) {
      setMessage(error instanceof DOMException && error.name === 'QuotaExceededError'
        ? 'Thiết bị hết chỗ lưu bản đồ.' : (error as Error).message);
    } finally { setBusy(false); }
  };
  const remove = async () => {
    if (busy) return;
    try {
      if (window.caches) await (await caches.open(cacheName)).delete(activePath);
      setInstalled(null);
      setRepairRequired(false);
      if (mode === 'offline') changeMode('hybrid');
      setMessage('Đã xóa gói bản đồ.');
    } catch {
      setMessage('Chưa xóa được gói bản đồ.');
    }
  };
  return { mode, changeMode, manifest, installed, busy, checked, repairRequired, message, install, remove,
    updateAvailable: Boolean(manifest && installed && manifest.sha256 !== installed.manifest.sha256) };
}
