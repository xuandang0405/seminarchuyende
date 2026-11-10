import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { apiClient } from '../services/apiClient';
import { palette } from '../../../../shared/brand';
import { loadDistrictBasemap } from './districtBasemap';
import { getSavedBasemap, onlineTileSources, type BasemapId } from '../services/mapStyles';
import type { ActiveMapPack, MapManifest, MapMode } from '../services/mapPack';

export interface Place {
  id?: string; _id?: string; name: string; description?: string; address?: string; category?: string;
  location?: { coordinates: [number, number] };
  trigger_radius?: number; audio_priority?: number;
  resolved_lang?: string; is_fallback?: boolean; narration_ready?: boolean;
}
export type Point = [number, number];
export const placeId = (place: Place) => place.id || place._id || '';
export function isPoint(lat: number, lng: number) {
  return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
}
export function pointOf(place: Place): Point | null {
  const point = place.location?.coordinates;
  if (!point || !isPoint(point[1], point[0])) return null;
  return [point[1], point[0]];
}

interface MapConfig {
  center?: { latitude: number; longitude: number };
  default_zoom?: number;
  bounds?: { min_latitude: number; min_longitude: number; max_latitude: number; max_longitude: number };
  style_url?: string;
  attribution?: string;
}

const districtBounds = L.latLngBounds([10.745, 106.685], [10.775, 106.720]);

function fitArea(map: L.Map, config: MapConfig | null) {
  const b = config?.bounds;
  const zoom = Math.max(3, Math.min(19, config?.default_zoom ?? 15));
  if (b && isPoint(b.min_latitude, b.min_longitude) && isPoint(b.max_latitude, b.max_longitude) &&
    b.min_latitude < b.max_latitude && b.min_longitude < b.max_longitude) {
    map.fitBounds([[b.min_latitude, b.min_longitude], [b.max_latitude, b.max_longitude]], { padding: [22, 22], maxZoom: zoom, animate: false });
  } else if (config?.center && isPoint(config.center.latitude, config.center.longitude)) {
    map.setView([config.center.latitude, config.center.longitude], zoom, { animate: false });
  } else {
    map.fitBounds(districtBounds, { padding: [22, 22], maxZoom: zoom, animate: false });
  }
}

export function TouristLeaflet({ places, selected, position, accuracy, onPickOrigin, dockOpen, route, approximate, focus, areaFocus, online, mode, manifest, installed, onSelect }: {
  places: Place[]; selected: Place | null; position: Point | null; accuracy?: number; onPickOrigin?: (point: Point) => void; dockOpen: boolean; route: Point[]; approximate: boolean; focus: number; areaFocus: number; online: boolean;
  mode: MapMode; manifest: MapManifest | null; installed: ActiveMapPack | null;
  onSelect: (place: Place, keyboard?: boolean) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map>();
  const areaView = useRef(true);
  const [config, setConfig] = useState<MapConfig | null>(null);
  const [localState, setLocalState] = useState<'loading' | 'ready' | 'unavailable'>('loading');
  const [outsideDistrict, setOutsideDistrict] = useState(false);
  const [tileState, setTileState] = useState<'loading' | 'ready' | 'unavailable'>('loading');
  const [tileRenderer, setTileRenderer] = useState<'osm' | 'openfreemap'>('osm');
  const [vectorReady, setVectorReady] = useState(false);
  const [retry, setRetry] = useState(0);
  const [localRetry, setLocalRetry] = useState(0);
  const [basemap, setBasemap] = useState<BasemapId>(getSavedBasemap);
  const select = useRef(onSelect);
  select.current = onSelect;

  // Lắng nghe sự kiện đổi kiểu bản đồ
  useEffect(() => {
    const onBasemapChange = (e: Event) => {
      const selected = (e as CustomEvent<BasemapId>).detail;
      if (selected) setBasemap(selected);
    };
    window.addEventListener('tourvoice:basemap_changed', onBasemapChange);
    return () => window.removeEventListener('tourvoice:basemap_changed', onBasemapChange);
  }, []);

  // Lắng nghe sự kiện phóng to / thu nhỏ từ nút bấm nổi FAB
  useEffect(() => {
    const onZoomAction = (e: Event) => {
      const delta = (e as CustomEvent<number>).detail;
      const instance = map.current;
      if (!instance) return;
      if (delta > 0) instance.zoomIn(1);
      else if (delta < 0) instance.zoomOut(1);
    };
    window.addEventListener('tourvoice:zoom', onZoomAction);
    return () => window.removeEventListener('tourvoice:zoom', onZoomAction);
  }, []);

  useEffect(() => {
    const element = host.current!;
    const instance = L.map(element, {
      scrollWheelZoom: true, // Cho phép lăn chuột phóng to thu nhỏ tự do
      zoomAnimation: true,
      fadeAnimation: true,
      markerZoomAnimation: true,
      zoomSnap: 1,
      zoomDelta: 1,
      wheelPxPerZoomLevel: 120,
      minZoom: 3, // Phóng to thu nhỏ toàn diện từ toàn cầu đến từng số nhà
      maxZoom: 21,
      doubleClickZoom: true,
      touchZoom: true,
      bounceAtZoomLimits: false,
      preferCanvas: true,
    });
    map.current = instance;
    instance.zoomControl.remove();
    instance.attributionControl?.setPosition('topright');
    instance.createPane('district-geometry').style.zIndex = '180';
    instance.createPane('district-labels').style.zIndex = '190';
    instance.createPane('district-vector').style.zIndex = '195';
    instance.createPane('street-vector').style.zIndex = '205';
    fitArea(instance, null);
    const cancelAreaView = () => { areaView.current = false; };
    instance.on('dragstart zoomstart', cancelAreaView);
    const size = new ResizeObserver(() => {
      instance.invalidateSize({ pan: false });
      if (areaView.current) {
        instance.fire('fitdistrict');
      }
    });
    size.observe(element);
    return () => { size.disconnect(); instance.remove(); map.current = undefined; areaView.current = true; };
  }, []);

  useEffect(() => {
    if (!online) return;
    const abort = new AbortController();
    apiClient.get<MapConfig>('/map/config', { signal: abort.signal })
      .then(result => { if (!abort.signal.aborted) setConfig(result); }).catch(() => {});
    return () => abort.abort();
  }, [online]);

  useEffect(() => {
    const instance = map.current!;
    const update = () => { fitArea(instance, config); areaView.current = true; };
    if (areaView.current) update();
    instance.on('fitdistrict', update);
    return () => { instance.off('fitdistrict', update); };
  }, [config]);

  useEffect(() => {
    if (areaFocus) map.current?.fire('fitdistrict');
  }, [areaFocus]);

  // The bundled district map stays beneath optional online layers.
  const vectorManifest = installed?.manifest || (online && mode !== 'offline' ? manifest : null);
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    if (basemap !== 'district' && mode !== 'offline') {
      setLocalState('ready');
      return;
    }
    const abort = new AbortController();
    let cleanup: (() => void) | undefined;
    setLocalState('loading');
    loadDistrictBasemap(instance, abort.signal).then(layer => {
      if (abort.signal.aborted) { layer.remove(); return; }
      const update = () => setOutsideDistrict(!layer.bounds.contains(instance.getCenter()) || instance.getZoom() < 13);
      instance.on('moveend', update);
      cleanup = () => { instance.off('moveend', update); layer.remove(); };
      update();
      setLocalState('ready');
    }).catch(() => { if (!abort.signal.aborted) setLocalState('unavailable'); });
    return () => { abort.abort(); cleanup?.(); };
  }, [localRetry]);

  useEffect(() => {
    setVectorReady(false);
    if (!vectorManifest || outsideDistrict) return;
    const instance = map.current!;
    const abort = new AbortController();
    let cleanup: (() => void) | undefined;
    import('./vectorBasemap').then(({ loadVectorBasemap }) => {
      if (!abort.signal.aborted) return loadVectorBasemap(instance, vectorManifest, installed?.blob, abort.signal);
    }).then(remove => {
      if (!remove) return;
      if (abort.signal.aborted) { remove(); return; }
      cleanup = remove;
      setVectorReady(true);
    }).catch(() => {});
    return () => { abort.abort(); cleanup?.(); };
  }, [vectorManifest, installed, outsideDistrict, localRetry]);

  const needsTiles = online && mode !== 'offline' && (
    basemap !== 'district' || mode === 'cloud' || outsideDistrict || (localState === 'unavailable' && !vectorReady)
  );
  useEffect(() => {
    const instance = map.current;
    if (!needsTiles || !instance) return;
    const sources = onlineTileSources(basemap, config?.style_url, config?.attribution);
    const abort = new AbortController();
    let layer: L.TileLayer | undefined;
    let timer: number | undefined;
    let removeVector: (() => void) | undefined;

    async function tryOnlineVector() {
      setTileState('loading');
      try {
        const { loadOnlineVectorBasemap } = await import('./vectorBasemap');
        const remove = await loadOnlineVectorBasemap(instance!, abort.signal);
        if (abort.signal.aborted) { remove(); return; }
        removeVector = remove;
        setTileRenderer('openfreemap');
        setTileState('ready');
      } catch {
        if (!abort.signal.aborted) setTileState('unavailable');
      }
    }

    function trySource(index: number) {
      window.clearTimeout(timer);
      layer?.off().remove();
      layer = undefined;
      const source = sources[index];
      if (!source) {
        if (basemap === 'osm') {
          void tryOnlineVector();
        } else {
          setTileState('unavailable');
        }
        return;
      }
      setTileState('loading');
      let loaded = 0;
      let failed = 0;
      const label = document.createElement('span');
      label.textContent = source.attribution;
      const current = L.tileLayer(source.url, {
        maxZoom: 21,
        maxNativeZoom: 19,
        subdomains: source.subdomains || ['0', '1', '2', '3'],
        attribution: label.outerHTML,
        updateWhenIdle: true,
        updateWhenZooming: false,
        keepBuffer: 6,
        opacity: 1,
      });
      layer = current;
      function finish() {
        window.clearTimeout(timer);
        if (loaded > 0) {
          setTileRenderer('osm');
          setTileState('ready');
        } else if (failed > 0) {
          queueMicrotask(() => { if (layer === current) trySource(index + 1); });
        }
      }
      current.on('loading', () => {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => {
          if (loaded === 0 && layer === current) trySource(index + 1);
        }, 4000);
      });
      current.on('tileload', () => {
        loaded++;
        if (loaded === 1) {
          setTileRenderer('osm');
          setTileState('ready');
        }
      });
      current.on('tileerror', () => { failed++; });
      current.on('load', finish);
      current.addTo(instance!);
    }
    trySource(0);
    return () => {
      abort.abort();
      window.clearTimeout(timer);
      layer?.off().remove();
      layer = undefined;
      removeVector?.();
    };
  }, [needsTiles, basemap, config?.attribution, config?.style_url, retry]);

  useEffect(() => {
    const instance = map.current!;
    if (!onPickOrigin) return;
    const pick = (event: L.LeafletMouseEvent) => onPickOrigin([event.latlng.lat, event.latlng.lng]);
    instance.on('click', pick);
    return () => { instance.off('click', pick); };
  }, [onPickOrigin]);

  useEffect(() => {
    const instance = map.current!;
    const markers = L.layerGroup().addTo(instance);
    function drawMarkers() {
      markers.clearLayers();
      const groups: { point: Point; pixel: L.Point; items: { place: Place; number: number }[] }[] = [];
      for (const [index, place] of places.entries()) {
        const point = pointOf(place);
        if (!point) continue;
        const pixel = instance.project(point);
        const item = { place, number: index + 1 };
        const group = groups.find(group => group.pixel.distanceTo(pixel) < 32);
        if (group) group.items.push(item);
        else groups.push({ point, pixel, items: [item] });
      }
      for (const { point, items } of groups) {
        const grouped = items.length > 1;
        const chosen = selected && items.some(item => placeId(item.place) === placeId(selected));
        const title = grouped ? `${items.length} điểm dừng gần nhau` : items[0].place.name;
        const size = grouped ? 34 : 30;
        const label = document.createElement('span');
        label.textContent = title;
        const marker = L.marker(point, {
          icon: L.divIcon({
            html: grouped ? '+' + items.length : String(items[0].number),
            className: `tv-pin${grouped ? ' tv-pin-cluster' : ''}${chosen ? ' tv-pin-active' : ''}`,
            iconSize: [size, size], iconAnchor: [size / 2, size / 2],
          }),
          title, alt: title, zIndexOffset: chosen ? 1000 : 0,
        }).bindTooltip(label, { direction: 'top', offset: [0, -size / 2] }).addTo(markers);
        if (!grouped) {
          marker.on('click', event => select.current(items[0].place, event.originalEvent instanceof KeyboardEvent));
          continue;
        }
        const choices = document.createElement('div');
        choices.className = 'tv-map-choices';
        const heading = document.createElement('strong');
        heading.textContent = 'Chọn điểm dừng';
        choices.append(heading);
        for (const item of items) {
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = `${item.number}. ${item.place.name}`;
          button.addEventListener('click', event => {
            marker.closePopup();
            select.current(item.place, event.detail === 0);
          });
          choices.append(button);
        }
        marker.bindPopup(choices, { maxWidth: 240, maxHeight: 224, offset: [0, -8] });
      }
    }
    instance.on('zoomend', drawMarkers);
    drawMarkers();
    return () => { instance.off('zoomend', drawMarkers); markers.remove(); };
  }, [places, selected]);
  useEffect(() => {
    if (!position || !isPoint(...position)) return;
    const layers = L.layerGroup().addTo(map.current!);
    if (accuracy !== undefined) L.circle(position, {
      radius: accuracy, color: '#1866a4', weight: 1.5, opacity: 0.8,
      fillColor: '#3386cc', fillOpacity: 0.12, interactive: false, className: 'tv-gps-accuracy',
      dashArray: accuracy > 100 ? '5 5' : undefined,
    }).addTo(layers);
    L.circleMarker(position, {
      radius: 7, color: 'white', weight: 2.5, fillColor: '#1866a4',
      fillOpacity: 1, interactive: false, className: 'tv-gps-dot',
    }).addTo(layers);
    return () => { layers.remove(); };
  }, [position, accuracy]);
  useEffect(() => {
    if (focus && position && isPoint(...position)) {
      areaView.current = false;
      const radius = Math.max(40, accuracy ?? 40);
      const bounds = L.latLng(position).toBounds(radius * 2);
      const desktop = window.matchMedia('(min-width: 1024px)').matches;
      map.current?.fitBounds(bounds, {
        paddingTopLeft: [desktop && dockOpen ? 400 : 24, desktop ? 96 : 180],
        paddingBottomRight: [76, desktop ? 48 : 200],
        maxZoom: 17,
      });
    }
    // Reframe only on explicit requests; tracking keeps the marker updated.
  }, [focus]);
  useEffect(() => {
    const point = selected && pointOf(selected);
    if (point) {
      areaView.current = false;
      map.current?.panTo(point);
    }
  }, [selected]);
  useEffect(() => {
    if (route.length < 2) return;
    areaView.current = false;
    const line = L.polyline(route, {
      className: 'tv-map-route', color: palette.accent, weight: 5, dashArray: approximate ? '7 8' : undefined, interactive: false,
    }).addTo(map.current!);
    const desktop = window.matchMedia('(min-width: 1024px)').matches;
    map.current?.fitBounds(line.getBounds(), {
      paddingTopLeft: [desktop && dockOpen ? 400 : 24, desktop ? 96 : 160],
      paddingBottomRight: [76, desktop ? 48 : 205],
      maxZoom: 17,
    });
    return () => { line.remove(); };
  }, [route, approximate]);
  const unavailable = needsTiles && tileState === 'unavailable';
  const status = outsideDistrict && (!online || mode === 'offline' || unavailable)
    ? 'Ngoài phạm vi bản đồ đã lưu. Chọn Về trung tâm Quận 4 để xem lại.'
    : unavailable ? (localState === 'ready' || vectorReady ? 'Bản đồ online tạm lỗi. Đang dùng bản đồ Quận 4.' : 'Chưa tải được bản đồ.')
    : needsTiles && tileState === 'loading' ? 'Đang tải bản đồ đường phố…'
    : localState === 'unavailable' && !vectorReady && !needsTiles ? 'Chưa tải được bản đồ Quận 4.'
    : localState === 'loading' && !vectorReady ? 'Đang tải bản đồ Quận 4…'
    : !online || mode === 'offline' ? 'Đang dùng bản đồ Quận 4 ngoại tuyến.' : '';
  const renderer = needsTiles && tileState === 'ready' ? tileRenderer
    : vectorReady ? 'pmtiles' : 'district';
  return <div className="tv-map-card" data-picking={Boolean(onPickOrigin)} data-tiles={needsTiles ? tileState : 'off'} data-basemap={localState} data-renderer={renderer}>
    <div ref={host} className="tv-leaflet" role="region" aria-label="Bản đồ tương tác Quận 4" />
    {status && <div className="tv-map-note" role="status">
      {status}
      {(outsideDistrict && (!online || mode === 'offline' || unavailable)) &&
        <button type="button" className="tv-link" onClick={() => map.current?.fire('fitdistrict')}>Về Quận 4</button>}
      {!outsideDistrict && (unavailable || (localState === 'unavailable' && !vectorReady)) &&
        <button type="button" className="tv-link" onClick={() => {
          if (localState === 'unavailable') setLocalRetry(value => value + 1);
          setRetry(value => value + 1);
        }}>Thử lại</button>}
    </div>}
  </div>;
}
