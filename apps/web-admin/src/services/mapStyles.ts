import { DEFAULT_ATTRIBUTION, DEFAULT_TILE_URL, validTileUrl } from './mapTiles';

export type BasemapId = 'google' | 'satellite' | 'carto' | 'osm' | 'district';

export interface BasemapOption {
  id: BasemapId;
  name: string;
  description: string;
  url?: string;
  subdomains?: string[];
  attribution?: string;
}

export const BASEMAP_STYLES: BasemapOption[] = [
  {
    id: 'google',
    name: 'Google Maps Chuẩn',
    description: 'Bản đồ giao thông, tên đường chi tiết, mượt mà và tải cực nhanh.',
    url: 'https://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    subdomains: ['0', '1', '2', '3'],
    attribution: '© Google Maps',
  },
  {
    id: 'satellite',
    name: 'Google Vệ tinh',
    description: 'Hình ảnh vệ tinh chân thực kết hợp mạng lưới đường phố sống động.',
    url: 'https://mt{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    subdomains: ['0', '1', '2', '3'],
    attribution: '© Google Maps Satellite',
  },
  {
    id: 'carto',
    name: 'Carto Voyager (Hiện đại)',
    description: 'Phong cách sáng thanh lịch, nổi bật các điểm du lịch & ẩm thực.',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    subdomains: ['a', 'b', 'c', 'd'],
    attribution: '© OpenStreetMap contributors, © CARTO',
  },
  {
    id: 'osm',
    name: 'OpenStreetMap',
    description: 'Bản đồ nguồn mở quốc tế.',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    subdomains: ['a', 'b', 'c'],
    attribution: '© OpenStreetMap contributors',
  },
  {
    id: 'district',
    name: 'Bản đồ Quận 4 Tối giản',
    description: 'Bản đồ vector địa phương Quận 4, nhẹ và tập trung khu vực.',
  },
];

const STORAGE_KEY = 'tourvoice_basemap_key';

export function getSavedBasemap(): BasemapId {
  const saved = localStorage.getItem(STORAGE_KEY) as BasemapId | null;
  if (saved && BASEMAP_STYLES.some(s => s.id === saved)) {
    return saved;
  }
  return 'google';
}

export function saveBasemap(id: BasemapId) {
  localStorage.setItem(STORAGE_KEY, id);
  window.dispatchEvent(new CustomEvent<BasemapId>('tourvoice:basemap_changed', { detail: id }));
}

export function onlineTileSources(basemapId: BasemapId = 'google', url?: string, attribution?: string) {
  const match = BASEMAP_STYLES.find(s => s.id === basemapId);
  const preferredUrl = match?.url || url || DEFAULT_TILE_URL;
  const preferredAttr = match?.attribution || attribution || DEFAULT_ATTRIBUTION;
  const subdomains = match?.subdomains || ['0', '1', '2', '3'];

  const sources = [
    { url: preferredUrl, attribution: preferredAttr, subdomains },
  ];

  if (preferredUrl !== DEFAULT_TILE_URL && validTileUrl(DEFAULT_TILE_URL)) {
    sources.push({ url: DEFAULT_TILE_URL, attribution: DEFAULT_ATTRIBUTION, subdomains: ['0', '1', '2', '3'] });
  }
  return sources;
}
