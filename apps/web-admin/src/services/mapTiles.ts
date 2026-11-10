import { apiClient } from './apiClient';

export const DEFAULT_TILE_URL = 'https://mt{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}';
export const DEFAULT_ATTRIBUTION = '© Google Maps';

export async function configureMapTiles(layer: any) {
  try {
    const config = await apiClient.get('/map/config');
    const url = config.style_url;
    if (typeof url !== 'string' || !validTileUrl(url)) return;
    layer.setUrl(url);
    const label = document.createElement('span');
    label.textContent = config.attribution || DEFAULT_ATTRIBUTION;
    const attribution = label.outerHTML;
    if (attribution && layer._map?.attributionControl) {
      layer._map.attributionControl.removeAttribution(layer.options.attribution);
      layer.options.attribution = attribution;
      layer._map.attributionControl.addAttribution(attribution);
    }
  } catch { /* Retain the interactive online default. Tiles are never bulk cached. */ }
}

export function validTileUrl(url: string) {
  try {
    const parsed = new URL(url.replace('{s}', '0').replace('{r}', ''));
    return parsed.protocol === 'https:' &&
      ['{x}', '{y}', '{z}'].every(part => url.includes(part));
  } catch { return false; }
}
