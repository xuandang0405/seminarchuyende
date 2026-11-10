import type L from 'leaflet';
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet';
import { addProtocol, setWorkerUrl, type LayerSpecification, type StyleSpecification } from 'maplibre-gl';
import { FileSource, PMTiles, Protocol } from 'pmtiles';
import type { MapManifest } from '../services/mapPack';
import 'maplibre-gl/dist/maplibre-gl.css';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

// MapLibre 6 loads its worker as a separate module. Keep it same-origin and precached.
setWorkerUrl(workerUrl);

const protocol = new Protocol();
addProtocol('pmtiles', protocol.tile);
const osm = '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · <a href="https://protomaps.com/">Protomaps</a>';
let webGlAvailable: boolean | undefined;

function requireWebGl() {
  if (webGlAvailable === undefined) {
    const gl = document.createElement('canvas').getContext('webgl2');
    webGlAvailable = Boolean(gl);
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
  }
  if (!webGlAvailable) throw new Error('Thiết bị đang dùng nền bản đồ tương thích.');
}

export async function loadOnlineVectorBasemap(map: L.Map, signal: AbortSignal) {
  requireWebGl();
  if (signal.aborted) throw signal.reason;
  const options = {
    style: 'https://tiles.openfreemap.org/styles/liberty', pane: 'street-vector',
    attributionControl: false as const, interactive: false, renderWorldCopies: false,
  };
  const layer = maplibreGL(options);
  const credit = '<a href="https://openfreemap.org/">OpenFreeMap</a> · © OpenMapTiles · <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>';
  try {
    layer.addTo(map);
    const container = layer.getContainer();
    container.style.opacity = '0';
    const renderer = layer.getMaplibreMap();
    await new Promise<void>((resolve, reject) => {
      function cleanup() {
        window.clearTimeout(timeout);
        signal.removeEventListener('abort', fail);
        renderer.off('idle', ready);
      }
      function fail() { cleanup(); reject(new Error('Nguồn bản đồ đường phố tạm lỗi.')); }
      function ready() {
        if (!renderer.queryRenderedFeatures().length) return;
        cleanup();
        resolve();
      }
      const timeout = window.setTimeout(fail, 8500);
      signal.addEventListener('abort', fail, { once: true });
      renderer.on('idle', ready);
      if (signal.aborted) fail();
    });
    container.style.opacity = '1';
    renderer.on('webglcontextlost', () => { container.style.opacity = '0'; });
    renderer.on('webglcontextrestored', () => { container.style.opacity = '1'; });
    map.attributionControl?.addAttribution(credit);
    return () => {
      layer.remove();
      map.attributionControl?.removeAttribution(credit);
    };
  } catch (error) {
    layer.remove();
    throw error;
  }
}

function districtStyle(source: string): StyleSpecification {
  const layers: LayerSpecification[] = [
    { id: 'background', type: 'background', paint: { 'background-color': '#f1f1e8' } },
    { id: 'parks', type: 'fill', source: 'district', 'source-layer': 'landuse',
      filter: ['in', ['get', 'kind'], ['literal', ['park', 'grass', 'garden', 'forest', 'wood']]],
      paint: { 'fill-color': '#dce9d0' } },
    { id: 'water', type: 'fill', source: 'district', 'source-layer': 'water',
      filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#b6dbe3' } },
    { id: 'streams', type: 'line', source: 'district', 'source-layer': 'water',
      filter: ['==', ['geometry-type'], 'LineString'], paint: { 'line-color': '#abd2db', 'line-width': 1.25 } },
    { id: 'buildings', type: 'fill', source: 'district', 'source-layer': 'buildings', minzoom: 15,
      filter: ['==', ['get', 'kind'], 'building'], paint: { 'fill-color': '#e6e2d7' } },
    { id: 'paths', type: 'line', source: 'district', 'source-layer': 'roads', minzoom: 15,
      filter: ['==', ['get', 'kind'], 'path'], paint: { 'line-color': '#d5cbb6', 'line-width': 1, 'line-dasharray': [2, 1] } },
    { id: 'roads', type: 'line', source: 'district', 'source-layer': 'roads',
      filter: ['in', ['get', 'kind'], ['literal', ['minor_road', 'major_road', 'highway']]],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': ['match', ['get', 'kind_detail'], ['motorway', 'trunk'], '#f8deb0', '#fffefa'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 0.8, 14,
          ['match', ['get', 'kind'], 'highway', 5, 'major_road', 3.2, 1.5], 18,
          ['match', ['get', 'kind'], 'highway', 15, 'major_road', 12, 5]],
      } },
    { id: 'road-names', type: 'symbol', source: 'district', 'source-layer': 'roads', minzoom: 12,
      filter: ['all', ['has', 'name'], ['any',
        ['in', ['get', 'kind'], ['literal', ['major_road', 'highway']]],
        ['all', ['>=', ['zoom'], 15], ['==', ['get', 'kind'], 'minor_road']],
      ]],
      layout: { 'symbol-placement': 'line', 'symbol-spacing': 145,
        'text-field': ['coalesce', ['get', 'name:vi'], ['get', 'name']],
        'text-font': ['Arial'], 'text-size': ['interpolate', ['linear'], ['zoom'], 12, 10, 17, 13] },
      paint: { 'text-color': '#4b4f43', 'text-halo-color': '#fbfaf4', 'text-halo-width': 1.35 } },
    { id: 'water-names', type: 'symbol', source: 'district', 'source-layer': 'water', minzoom: 12,
      filter: ['all', ['has', 'name'], ['==', ['geometry-type'], 'LineString']],
      layout: { 'text-field': ['get', 'name'], 'text-font': ['Arial'], 'text-size': 11, 'symbol-placement': 'line' },
      paint: { 'text-color': '#2c6677', 'text-halo-color': '#f6fbfa', 'text-halo-width': 1.2 } },
    { id: 'place-names', type: 'symbol', source: 'district', 'source-layer': 'places', minzoom: 12,
      filter: ['all', ['has', 'name'], ['<=', ['coalesce', ['get', 'min_zoom'], 14], ['+', ['zoom'], 0.8]],
        ['any', ['>=', ['zoom'], 16], ['!=', ['index-of', 'Khu phố ', ['get', 'name']], 0]]],
      layout: { 'text-field': ['get', 'name'], 'text-font': ['Arial Bold'], 'text-size': 12, 'text-max-width': 12 },
      paint: { 'text-color': '#31584c', 'text-halo-color': '#fffef8', 'text-halo-width': 1.5 } },
    { id: 'district-name', type: 'symbol', source: 'district', 'source-layer': 'pois', minzoom: 12,
      filter: ['==', ['get', 'name'], 'Quận 4'],
      layout: { 'text-field': ['get', 'name'], 'text-font': ['Arial Bold'], 'text-size': 14, 'text-allow-overlap': true },
      paint: { 'text-color': '#244e41', 'text-halo-color': '#fffef8', 'text-halo-width': 1.5 } },
  ];
  return { version: 8, sources: { district: { type: 'vector', url: source } }, layers };
}

export async function loadVectorBasemap(map: L.Map, manifest: MapManifest, local: Blob | undefined, signal: AbortSignal) {
  requireWebGl();
  const key = local ? `${manifest.version}-${manifest.sha256}.pmtiles` : new URL(manifest.archive, location.origin).href;
  const archive = new PMTiles(local ? new FileSource(new File([local], key)) : key);
  const header = await archive.getHeader();
  if (signal.aborted || header.tileType !== 1) throw new Error('Gói bản đồ chưa sẵn sàng.');
  protocol.add(archive);
  const options = { style: districtStyle(`pmtiles://${key}`), pane: 'district-vector', attributionControl: false as const,
    interactive: false, renderWorldCopies: false };
  const layer = maplibreGL(options);
  const remove = () => { layer.remove(); protocol.tiles.delete(key); };
  try {
    layer.addTo(map);
    const container = layer.getContainer();
    container.style.opacity = '0';
    const renderer = layer.getMaplibreMap();
    renderer.on('webglcontextlost', () => { container.style.opacity = '0'; });
    renderer.on('webglcontextrestored', () => { container.style.opacity = '1'; });
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        window.clearTimeout(timeout);
        signal.removeEventListener('abort', fail);
        renderer.off('idle', ready);
      };
      const ready = () => { cleanup(); resolve(); };
      const fail = () => { cleanup(); reject(new Error('Chưa hiển thị được bản đồ PMTiles.')); };
      const timeout = window.setTimeout(fail, 5500);
      signal.addEventListener('abort', fail, { once: true });
      renderer.on('idle', ready);
      if (signal.aborted) fail();
    });
    container.style.opacity = '1';
    map.attributionControl?.addAttribution(osm);
    return () => {
      remove();
      map.attributionControl?.removeAttribution(osm);
    };
  } catch (error) {
    remove();
    throw error;
  }
}
