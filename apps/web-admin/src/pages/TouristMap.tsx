import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Download,
  Focus,
  Headphones,
  Landmark,
  Languages,
  Layers,
  LocateFixed,
  MapPin,
  Minus,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Route,
  Search,
  UserRound,
  Utensils,
  Waves,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ApiError, apiClient } from '../services/apiClient';
import { AnalyticsConsent, trackQrScan, useVisitorAnalytics } from '../services/analytics';
import { useWebPresence } from '../services/liveTelemetry';
import { downloadOfflineTour, getOfflineTours, removeOfflineTour } from '../services/offline';
import { useMapPack } from '../services/mapPack';
import { usePublicCatalog, type Tour } from '../services/publicCatalog';
import { prepareNarrationLocale, prepareNearbyNarrations } from '../services/narration';
import { setAppLanguage, type SupportedLanguage } from '../i18n';
import { publicUi } from '../i18n/publicUi';
import { GeofenceEngine, calculateDistanceMeters } from '../../../../shared/geofence';
import { languages, categoryLabel, searchText } from '../../../../shared/brand';
import { TouristLeaflet, isPoint, placeId, pointOf, type Place, type Point } from './TouristLeaflet';
import { TouristCheckout, formatVnd, type CheckoutOrder } from './TouristCheckout';
import { useTouristNarration } from './useTouristNarration';
import { TouristPlayer } from './TouristPlayer';
import { NarrationDialog } from './NarrationDialog';
import { gpsError, readCurrentPosition, ROUTE_ACCURACY, usableFix } from '../services/geolocation';
import { BasemapSelector } from './BasemapSelector';
import './TouristMap.css';

type BrowseTab = 'places' | 'tours' | 'saved';
const idPath = (id: string) => encodeURIComponent(id);
type Access = { can_download: boolean; has_entitlement: boolean; can_play_full_tour: boolean; can_preview: boolean };
type OfflinePack = { tour_id: string; tour_name: string; pois: Place[]; total_bytes: number };
type Directions = {
  geometry?: { coordinates?: [number, number][] };
  distance_display?: string;
  duration_display?: string;
  steps?: { instruction: string; distance_m?: number }[];
  approximate?: boolean;
};
type MenuItem = { id?: string; _id?: string; name: string; price_amount?: number; price?: number };

const LANG_FLAGS: Record<string, string> = {
  vi: '🇻🇳',
  en: '🇬🇧',
  fr: '🇫🇷',
  ja: '🇯🇵',
  ko: '🇰🇷',
  zh: '🇨🇳',
};

function routePoints(geometry: Directions['geometry']): Point[] {
  const points = geometry?.coordinates;
  if (!Array.isArray(points) || points.length < 2 || points.some(point => !Array.isArray(point) || !isPoint(point[1], point[0]))) {
    return [];
  }
  return points.map(([lng, lat]) => [lat, lng]);
}

export function TouristMap() {
  const { user, status: authStatus } = useAuth();
  const { search } = useLocation();
  const [lang, setLang] = useState(() => {
    const value = localStorage.getItem('app_language');
    return languages.some(([id]) => id === value) ? value! : 'vi';
  });
  const ui = publicUi(lang);
  useWebPresence();
  useVisitorAnalytics(lang);
  const [online, setOnline] = useState(navigator.onLine);
  const mapPack = useMapPack(online);
  const [reload, setReload] = useState(0);
  const { places, tours, loading, failed, contentLang } = usePublicCatalog(lang, online, reload);
  const [deepLinkError, setDeepLinkError] = useState('');
  const [tab, setTab] = useState<BrowseTab>('places');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [selected, setSelected] = useState<Place | null>(null);
  const [tour, setTour] = useState<Tour | null>(null);
  const [access, setAccess] = useState<Access | null>(null);
  const [accessRevision, setAccessRevision] = useState(0);
  const [receipt, setReceipt] = useState<{ tourId: string; userId: string; order: CheckoutOrder }>();
  const [tourError, setTourError] = useState('');
  const [offlinePacks, setOfflinePacks] = useState<OfflinePack[]>([]);
  const [downloadText, setDownloadText] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [gps, setGps] = useState(false);
  const [autoPlay, setAutoPlay] = useState(true);
  const [fix, setFix] = useState<GeolocationPosition | null>(null);
  const [locating, setLocating] = useState(false);
  const [routeBusy, setRouteBusy] = useState(false);
  const [pickOrigin, setPickOrigin] = useState<Place | null>(null);
  const accuracy = fix?.coords.accuracy;
  const position = useMemo<Point | null>(() => fix && fix.coords.accuracy <= 1000
    ? [fix.coords.latitude, fix.coords.longitude] : null, [fix]);
  const [gpsMessage, setGpsMessage] = useState('');
  const [focus, setFocus] = useState(0);
  const [areaFocus, setAreaFocus] = useState(0);
  const [directions, setDirections] = useState<Directions | null>(null);
  const [routeMessage, setRouteMessage] = useState('');
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [preparation, setPreparation] = useState<{ busy: boolean; text: string }>();

  // Responsive UI state: Desktop Dock & Mobile Sheet
  const [dockOpen, setDockOpen] = useState(true);
  const [playerDock, setPlayerDock] = useState<HTMLDivElement | null>(null);
  const [snap, setSnap] = useState<'peek' | 'half' | 'full'>('peek');
  const [layerModalOpen, setLayerModalOpen] = useState(false);

  const panel = useRef<HTMLElement>(null);
  const routeRequest = useRef<AbortController>();
  const routeCache = useRef<Map<string, Directions>>(new Map());



  const locationRequest = useRef<AbortController>();
  const downloadRequest = useRef<AbortController>();
  const localeRequest = useRef<AbortController>();
  const hotsetRequest = useRef<AbortController>();
  const hotsetHistory = useRef({ key: '', nextAt: 0 });
  const engine = useRef(new GeofenceEngine());
  const qrPlace = useRef('');
  const trackedQr = useRef('');

  const narration = useTouristNarration({
    userId: user?.id,
    lang,
    online,
    onStop: id => engine.current.suppressCurrentZone(id),
    onComplete: id => engine.current.markPlaybackCompleted(id),
  });

  const selectedId = selected && placeId(selected);
  const tourId = tour && placeId(tour);
  const offlinePack = offlinePacks.find(pack => pack.tour_id === tourId);
  const packSaved = Boolean(offlinePack);
  const accountHref = user ? '/account' : '/client/login';

  useEffect(() => {
    setPreparation(undefined);
    return () => localeRequest.current?.abort();
  }, [selectedId, lang]);

  useEffect(() => {
    const connect = () => setOnline(navigator.onLine);
    window.addEventListener('online', connect);
    window.addEventListener('offline', connect);
    return () => {
      window.removeEventListener('online', connect);
      window.removeEventListener('offline', connect);
      routeRequest.current?.abort();
      locationRequest.current?.abort();
    };
  }, []);

  useEffect(() => {
    let stale = false;
    setOfflinePacks([]);
    getOfflineTours(user?.id, lang).then(packs => {
      if (!stale) setOfflinePacks(packs);
    });
    return () => {
      stale = true;
      downloadRequest.current?.abort();
    };
  }, [user?.id, lang]);

  useEffect(() => {
    setDeepLinkError('');
    if (!online) return;
    const params = new URLSearchParams(search);
    const code = params.get('qr') || params.get('code');
    const id = params.get('id') || params.get('tour');
    const type = params.get('tour') ? 'tour' : params.get('type');
    const controller = new AbortController();

    const open = async () => {
      try {
        if (code) {
          const result = await apiClient.get<{ target_type: string; tour?: Tour; poi?: Place }>('/qr/' + idPath(code), {
            signal: controller.signal,
          });
          if (controller.signal.aborted) return;
          if (trackedQr.current !== code && (result.poi || result.tour)) {
            const target = result.poi ? { poi_id: placeId(result.poi) } : { tour_id: placeId(result.tour!) };
            if (trackQrScan(lang, target)) trackedQr.current = code;
          }
          if (result.target_type === 'tour' && result.tour) {
            setTour(result.tour);
            setTab('tours');
            setDockOpen(true);
            setSnap('half');
          }
          if (result.target_type === 'poi' && result.poi) {
            qrPlace.current = placeId(result.poi);
            setSelected(result.poi);
            setDockOpen(true);
            setSnap('half');
          }
        } else if (id && type === 'tour') {
          setTour({ id, name: '' });
          setTab('tours');
          setDockOpen(true);
          setSnap('half');
        } else if (id && type === 'poi') {
          const place = await apiClient.get<Place>('/pois/' + idPath(id), { params: { lang }, signal: controller.signal });
          if (!controller.signal.aborted) {
            qrPlace.current = id;
            setSelected(place);
            setDockOpen(true);
            setSnap('half');
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setDeepLinkError((error as Error).message);
          setDockOpen(true);
          setSnap('half');
        }
      }
    };
    void open();
    return () => controller.abort();
  }, [online, search, lang]);

  useEffect(() => {
    if (!tourId || !online) return;
    const controller = new AbortController();
    setTourError('');
    apiClient
      .get<Tour>('/tours/' + idPath(tourId), { params: { lang }, signal: controller.signal })
      .then(data => {
        if (!controller.signal.aborted) setTour(data);
      })
      .catch(error => {
        if (!controller.signal.aborted) setTourError(error.message);
      });
    return () => controller.abort();
  }, [tourId, lang, online, reload]);

  useEffect(() => {
    setAccess(null);
    if (!tourId || !online || authStatus === 'loading') return;
    const controller = new AbortController();
    apiClient
      .get<Access>('/tours/' + idPath(tourId) + '/access', { signal: controller.signal })
      .then(data => {
        if (!controller.signal.aborted) setAccess(data);
      })
      .catch(error => {
        if (!controller.signal.aborted) setTourError(error.message);
      });
    return () => controller.abort();
  }, [tourId, online, user?.id, authStatus, accessRevision, reload]);

  useEffect(() => {
    setMenu([]);
    if (!selectedId || !online) return;
    const controller = new AbortController();
    apiClient
      .get<MenuItem[]>('/pois/' + idPath(selectedId) + '/menu', { signal: controller.signal })
      .then(data => {
        if (!controller.signal.aborted) setMenu(data);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [selectedId, online]);

  const visiblePlaces = useMemo(
    () =>
      online && places.length
        ? places
        : [...new Map([...offlinePacks.flatMap(pack => pack.pois), ...places].map(p => [placeId(p), p])).values()],
    [online, places, offlinePacks]
  );

  const tourPlaces = useMemo(() => {
    if (!tour) return [];
    const byId = new Map(visiblePlaces.map(item => [placeId(item), item]));
    if (tour.pois?.length) return tour.pois.map(item => byId.get(placeId(item)) || item);
    if (offlinePack) return offlinePack.pois;
    const ids =
      tour.poi_ids ??
      tour.stops
        ?.slice()
        .sort((a, b) => (a.stop_order ?? 0) - (b.stop_order ?? 0))
        .map(stop => stop.poi_id);
    return (ids || []).flatMap(id => byId.get(id) || []);
  }, [tour, visiblePlaces, offlinePack]);

  const place = selected && (visiblePlaces.find(item => placeId(item) === selectedId) || selected);
  const candidates = useMemo(
    () => (tour ? tourPlaces : visiblePlaces).map(p => ({ ...p, _id: placeId(p) })),
    [tour, tourPlaces, visiblePlaces]
  );
  const offlineAudioIds = useMemo(
    () =>
      new Set(
        offlinePacks
          .filter(pack => !tourId || pack.tour_id === tourId)
          .flatMap(pack => pack.pois.map(placeId))
      ),
    [offlinePacks, tourId]
  );
  const playableCandidates = useMemo(
    () => online ? candidates : candidates.filter(item => offlineAudioIds.has(item._id)),
    [candidates, online, offlineAudioIds]
  );

  const gpsSample = useRef<GeolocationPosition | null>(null);
  const lastDecision = useRef(-Infinity);
  const gpsAction = useRef<(sample: GeolocationPosition) => void>();
  gpsAction.current = sample => {
    const now = performance.now();
    if (locationRequest.current || routeRequest.current || pickOrigin || layerModalOpen || !usableFix(sample) || !autoPlay || narration.active.current || narration.trial || narration.gateReason || now - lastDecision.current < 4900)
      return;
    lastDecision.current = now;
    const hit = engine.current.evaluateLocation(
      {
        latitude: sample.coords.latitude,
        longitude: sample.coords.longitude,
        accuracyM: sample.coords.accuracy,
        capturedAt: sample.timestamp,
      },
      playableCandidates
    );
    if (hit) {
      setSelected(hit.poi);
      setSnap('half');
      void narration.play({ place: hit.poi, tourId: tourId || undefined, source: 'gps' });
    }
  };

  useEffect(() => {
    if (!gps) return;
    if (!window.isSecureContext || !navigator.geolocation) {
      setGpsMessage(gpsError(1));
      setGps(false);
      return;
    }
    const watch = navigator.geolocation.watchPosition(
      sample => {
        if (!usableFix(sample) || locationRequest.current || routeRequest.current) return;
        const previous = gpsSample.current;
        if (previous && (sample.timestamp < previous.timestamp ||
          (sample.timestamp - previous.timestamp < 15000 &&
            sample.coords.accuracy > Math.max(35, previous.coords.accuracy * 2)))) return;
        gpsSample.current = sample;
        setFix(sample);
        setGpsMessage('');
        gpsAction.current?.(sample);
      },
      error => {
        if (locationRequest.current || routeRequest.current) return;
        if (error.code === 1) {
          gpsSample.current = null;
          setFix(null);
          setGps(false);
        }
        engine.current.clearPendingEntries();
        setGpsMessage(gpsError(error.code, error.message));
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }
    );
    return () => navigator.geolocation.clearWatch(watch);
  }, [gps]);

  useEffect(() => {
    if (!fix) return;
    const timer = window.setTimeout(() => {
      if (gpsSample.current === fix) gpsSample.current = null;
      setFix(current => current === fix ? null : current);
    }, Math.max(0, 30000 - (Date.now() - fix.timestamp)));
    return () => window.clearTimeout(timer);
  }, [fix]);

  useEffect(() => {
    engine.current.clearPendingEntries();
    lastDecision.current = -Infinity;
    if (!gps || !autoPlay) return;
    const reconcile = () => {
      const sample = gpsSample.current;
      if (sample && Date.now() - sample.timestamp <= 30000) gpsAction.current?.(sample);
      else engine.current.clearPendingEntries();
    };
    reconcile();
    const interval = window.setInterval(reconcile, 5000);
    return () => window.clearInterval(interval);
  }, [gps, autoPlay, tourId, lang]);

  useEffect(() => () => hotsetRequest.current?.abort(), [lang, online, gps, autoPlay, user?.id]);

  useEffect(() => {
    if (
      !online ||
      !gps ||
      !autoPlay ||
      !position ||
      authStatus === 'loading' ||
      contentLang !== lang ||
      !gpsSample.current ||
      gpsSample.current.coords.accuracy > 100 ||
      Date.now() < hotsetHistory.current.nextAt
    )
      return;
    const nearby = candidates
      .flatMap(item => {
        const point = pointOf(item);
        const distance = point ? calculateDistanceMeters(...position, ...point) : Infinity;
        return distance <= 1500 ? [{ item, distance }] : [];
      })
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 10);
    const ids = nearby
      .filter(({ item }) => item.is_fallback || item.narration_ready === false)
      .slice(0, 3)
      .map(({ item }) => placeId(item));
    const key = lang + ':' + ids.slice().sort().join(',');
    if (!ids.length || key === hotsetHistory.current.key) return;
    hotsetHistory.current = { key, nextAt: Date.now() + 60000 };
    const controller = new AbortController();
    hotsetRequest.current = controller;
    prepareNearbyNarrations(ids, lang, Boolean(user), controller.signal).catch(error => {
      if (!controller.signal.aborted) {
        hotsetHistory.current = {
          key: '',
          nextAt: Date.now() + (error instanceof ApiError && error.statusCode === 429 ? 600000 : 60000),
        };
      }
    });
  }, [online, gps, autoPlay, position, authStatus, contentLang, lang, candidates, user?.id]);

  const closeRoute = () => {
    routeRequest.current?.abort();
    routeRequest.current = undefined;
    setRouteBusy(false);
    setPickOrigin(null);
    setDirections(null);
    setRouteMessage('');
  };

  const selectPlace = useCallback((item: Place, _fromMap = false, _focusPreview = false) => {
    setSelected(item);
    closeRoute();
    setDockOpen(true);
    setSnap('half');
  }, []);

  const selectTour = useCallback((item: Tour) => {
    setTab(current => (current === 'saved' ? 'saved' : 'tours'));
    setTour(item);
    setSelected(null);
    setAccess(null);
    setTourError('');
    setDownloadText('');
    closeRoute();
    setDockOpen(true);
    setSnap('half');
  }, []);

  const switchTab = (value: BrowseTab) => {
    setTab(value);
    setQuery('');
    setSelected(null);
    setTour(null);
    setDownloadText('');
    closeRoute();
  };

  const searchCatalog = (value: string) => {
    if (selected || tour || tab === 'saved') switchTab(tab === 'tours' ? 'tours' : 'places');
    setQuery(value);
    setDockOpen(true);
    if (snap === 'peek') setSnap('half');
  };

  const locate = async () => {
    if (locationRequest.current) return;
    const controller = new AbortController();
    locationRequest.current = controller;
    setLocating(true);
    setGpsMessage('');
    try {
      const sample = await readCurrentPosition(controller.signal);
      gpsSample.current = sample;
      setFix(sample);
      if (sample.coords.accuracy <= 1000) setFocus(value => value + 1);
      setGps(true);
    } catch (error) {
      if (!controller.signal.aborted) {
        setFix(null);
        gpsSample.current = null;
        setGpsMessage((error as Error).message);
      }
    } finally {
      if (locationRequest.current === controller) {
        locationRequest.current = undefined;
        setLocating(false);
      }
    }
  };

  const prepareLocale = async (item: Place) => {
    const controller = new AbortController();
    localeRequest.current?.abort();
    localeRequest.current = controller;
    setPreparation({ busy: true, text: ui.preparing });
    try {
      const result = await prepareNarrationLocale(placeId(item), lang, Boolean(user), controller.signal);
      if (controller.signal.aborted) return;
      setPreparation({
        busy: false,
        text:
          result.status === 'ready'
            ? 'Bản thuyết minh đã sẵn sàng.'
            : 'Đã đưa bản thuyết minh vào hàng đợi. Bạn vẫn có thể nghe bản hiện có.',
      });
      if (result.status === 'ready') setReload(value => value + 1);
    } catch (error) {
      if (!controller.signal.aborted) setPreparation({ busy: false, text: (error as Error).message });
    }
  };

  const showRoute = async (walkTo?: Place, manualOrigin?: Point) => {
    if (!walkTo && !tourId) return;
    if (!online) { setRouteMessage('Cần kết nối mạng để tính đường đi.'); return; }
    closeRoute();
    const controller = new AbortController();
    routeRequest.current = controller;
    setRouteBusy(true);
    try {
      let result: Directions;
      if (walkTo) {
        let origin = manualOrigin;
        if (!origin) {
          if (position && fix && usableFix(fix)) {
            origin = position;
          } else if (gpsSample.current && usableFix(gpsSample.current)) {
            origin = [gpsSample.current.coords.latitude, gpsSample.current.coords.longitude];
          } else {
            setRouteMessage('Đang lấy vị trí GPS thực tế…');
            try {
              const sample = await readCurrentPosition(controller.signal, { targetAccuracy: 150, timeout: 3500 });
              if (controller.signal.aborted) return;
              setGpsMessage('');
              setFix(sample);
              gpsSample.current = sample;
              origin = [sample.coords.latitude, sample.coords.longitude];
            } catch {
              if (controller.signal.aborted) return;
              // TUYỆT ĐỐI KHÔNG DÙNG TỌA ĐỘ ẢO/FAKE. Yêu cầu người dùng bật GPS hoặc chọn điểm xuất phát thật trên bản đồ.
              setPickOrigin(walkTo);
              setRouteMessage('Chưa có GPS thực tế. Hãy chạm vào bản đồ để chọn điểm xuất phát thật của bạn.');
              setRouteBusy(false);
              return;
            }
          }
        }

        const cacheKey = `${origin[0].toFixed(5)},${origin[1].toFixed(5)}->${placeId(walkTo)}:${lang}`;
        if (routeCache.current.has(cacheKey)) {
          const cached = routeCache.current.get(cacheKey)!;
          setDirections(cached);
          setRouteBusy(false);
          setRouteMessage('');
          if (window.matchMedia('(max-width: 1023px)').matches) setSnap('peek');
          return;
        }

        setRouteMessage('Đang tính đường đi bộ thực tế theo mạng lưới đường sá…');
        result = await apiClient.post<Directions>(
          '/routes/preview',
          {
            origin: { latitude: origin[0], longitude: origin[1] },
            destination_poi_id: placeId(walkTo),
            mode: 'walking',
            locale: lang,
          },
          { signal: controller.signal }
        );
        routeCache.current.set(cacheKey, result);
      } else {
        const cacheKey = `tour:${tourId}:${lang}`;
        if (routeCache.current.has(cacheKey)) {
          const cached = routeCache.current.get(cacheKey)!;
          setDirections(cached);
          setRouteBusy(false);
          setRouteMessage('');
          if (window.matchMedia('(max-width: 1023px)').matches) setSnap('peek');
          return;
        }

        setRouteMessage('Đang tải lộ trình các chặng tour thực tế…');
        const summary = await apiClient.get<{
          geometry?: Directions['geometry'];
          stop_count: number;
          total_distance_display: string;
          total_duration_display: string;
          legs: Directions[];
        }>('/routes/tour/' + idPath(tourId!), {
          params: { locale: lang },
          signal: controller.signal,
        });
        const approximate = summary.legs.length < summary.stop_count - 1;
        result = approximate
          ? {
              approximate,
              geometry: {
                coordinates: tourPlaces.flatMap(item => {
                  const point = pointOf(item);
                  return point ? [[point[1], point[0]] as [number, number]] : [];
                }),
              },
            }
          : {
              geometry: summary.geometry,
              distance_display: summary.total_distance_display,
              duration_display: summary.total_duration_display,
              steps: summary.legs.flatMap(leg => leg.steps || []),
            };
        routeCache.current.set(cacheKey, result);
      }
      if (!controller.signal.aborted) {
        if (!routePoints(result.geometry).length) {
          setRouteMessage('Không tìm thấy đường đi bộ thực tế giữa hai địa điểm này.');
          return;
        }
        setDirections(result);
        setRouteMessage('');
        if (window.matchMedia('(max-width: 1023px)').matches) setSnap('peek');
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setRouteMessage((error as Error).message);
        if (walkTo) setSnap('half');
      }
    } finally {
      if (routeRequest.current === controller) {
        routeRequest.current = undefined;
        setRouteBusy(false);
      }
    }
  };

  const download = async () => {
    if (!tourId || !user) return;
    const controller = new AbortController();
    downloadRequest.current = controller;
    setDownloading(true);
    setDownloadText('Đang chuẩn bị gói ngoại tuyến…');
    try {
      await downloadOfflineTour(tourId, user.id, lang, setDownloadText, controller.signal);
      const packs = await getOfflineTours(user.id, lang);
      if (!controller.signal.aborted) setOfflinePacks(packs);
    } catch (error) {
      if (!controller.signal.aborted) setDownloadText((error as Error).message);
    } finally {
      setDownloading(false);
    }
  };

  const remove = async () => {
    if (!user || !tourId) return;
    try {
      await removeOfflineTour(user.id, lang, tourId);
      setOfflinePacks(packs => packs.filter(pack => pack.tour_id !== tourId));
      setDownloadText('Đã xóa gói ngoại tuyến trên thiết bị này.');
    } catch (error) {
      setDownloadText((error as Error).message);
    }
  };

  const term = searchText(query.trim());
  const searchTokens = useMemo(() => term.split(/\s+/).filter(Boolean), [term]);
  const matches = useCallback(
    (item: Place) => {
      if (!searchTokens.length) return true;
      const haystack = searchText(
        [item.name, item.description, item.address, categoryLabel(item.category), item.category]
          .filter(Boolean)
          .join(' ')
      );
      return searchTokens.every(tok => haystack.includes(tok));
    },
    [searchTokens]
  );
  const filteredPlaces = useMemo(
    () =>
      visiblePlaces.filter(item => {
        // Loại bỏ địa điểm không có tọa độ hoặc tọa độ ảo/fake (0, 0)
        const pt = pointOf(item);
        if (!pt || !isPoint(pt[0], pt[1]) || (Math.abs(pt[0]) < 0.0001 && Math.abs(pt[1]) < 0.0001)) {
          return false;
        }
        const matchCategory = !category || categoryLabel(item.category) === category;
        if (searchTokens.length > 0) {
          return matches(item);
        }
        return matchCategory;
      }),
    [visiblePlaces, category, searchTokens, matches]
  );
  const categories = useMemo(() => [...new Set(visiblePlaces.map(item => categoryLabel(item.category)))], [visiblePlaces]);
  const tourTitle = (item: Tour) =>
    item.localizations?.[lang]?.name || item.localizations?.[lang]?.title || item.name || 'Tuyến tham quan';
  const browseTours = tours.filter(item => matches({ ...item, name: tourTitle(item) }));
  const browsePacks = offlinePacks.filter(
    pack =>
      tab === 'saved' ||
      (!online && !tours.some(item => placeId(item) === pack.tour_id) && searchText(pack.tour_name).includes(term))
  );
  const price = tour?.price_amount || 0;
  const paid = Boolean(tour?.is_paid || price > 0);
  const mapPlaces = useMemo(() => {
    const items = tour ? tourPlaces : tab === 'places' ? filteredPlaces : visiblePlaces;
    return place && !items.some(item => placeId(item) === selectedId) ? [...items, place] : items;
  }, [tour, tourPlaces, tab, filteredPlaces, visiblePlaces, place, selectedId]);
  const mapRoute = useMemo(() => routePoints(directions?.geometry), [directions]);
  const audioError = narration.error?.placeId === selectedId ? narration.error.message : '';
  const playPlace = (item: Place) =>
    void narration.play({
      place: item,
      tourId: tourId || undefined,
      source: qrPlace.current === placeId(item) ? 'qr' : 'manual',
    });
  const audioDisabled = Boolean(narration.busy) || authStatus === 'loading';

  const displayDistance = (item: Place) => {
    const point = pointOf(item);
    if (!position || !point || accuracy === undefined || accuracy > ROUTE_ACCURACY) return null;
    const metres = calculateDistanceMeters(...position, ...point);
    return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
  };

  const toggleSnap = () => {
    setPickOrigin(null);
    setSnap(current => (current === 'peek' ? 'half' : 'peek'));
  };

  // Back button handling on mobile (Mục 3 skill mobile)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !document.querySelector('dialog:modal')) {
        if (layerModalOpen) {
          setLayerModalOpen(false);
          return;
        }
        if (selected) {
          setSelected(null);
          closeRoute();
        } else if (tour) {
          setTour(null);
          closeRoute();
        } else if (snap !== 'peek') {
          setSnap('peek');
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selected, tour, snap, layerModalOpen]);

  const placeRow = (item: Place, index: number, ordered = false) => {
    const kind = categoryLabel(item.category);
    const Icon =
      kind === 'Ẩm thực' ? Utensils : kind === 'Cầu và cảng' ? Waves : kind === 'Di tích' || kind === 'Bảo tàng' ? Landmark : MapPin;
    const distance = displayDistance(item);
    const isCurrent = selectedId === placeId(item);

    return (
      <li key={placeId(item)}>
        <button
          type="button"
          className="tv-card-item"
          aria-current={isCurrent ? 'true' : undefined}
          onClick={() => selectPlace(item)}
        >
          <span className="tv-card-icon" aria-hidden="true">
            {ordered ? String(index + 1).padStart(2, '0') : <Icon size={20} />}
          </span>
          <span className="tv-card-text">
            <small className="tv-card-kicker">{kind}</small>
            <strong>{item.name}</strong>
            {item.address && <small>{item.address}</small>}
          </span>
          {distance && <span className="tv-card-distance">{distance}</span>}
          <ChevronRight size={18} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
        </button>
      </li>
    );
  };

  return (
    <div className="tv-shell" data-sheet={snap} data-detail={Boolean(selected || tour)}>
      {/* Tầng 1: Full-Bleed Map Viewport (--z-map) */}
      <section className="tv-map-viewport" aria-label="Bản đồ không gian du lịch">
        <TouristLeaflet
          places={mapPlaces}
          selected={place}
          position={position}
          accuracy={accuracy}
          dockOpen={dockOpen}
          onPickOrigin={pickOrigin ? point => void showRoute(pickOrigin, point) : undefined}
          route={mapRoute}
          approximate={Boolean(directions?.approximate)}
          focus={focus}
          areaFocus={areaFocus}
          online={online}
          mode={mapPack.mode}
          manifest={mapPack.manifest}
          installed={mapPack.installed}
          onSelect={(item, keyboard) => selectPlace(item, true, keyboard)}
        />
      </section>

      {/* Tầng 2: Top Floating Glass HUD (--z-hud) */}
      <header className="tv-hud-top" role="banner">
        {/* Row 1: Brand (Left) + Desktop Search (Center) + Actions Group (Right) */}
        <div className="tv-hud-row-top">
          {/* Brand Logo Pill */}
          <Link
            to="/client"
            onClick={() => {
              switchTab('places');
              setCategory('');
            }}
            className="tv-brand-pill tv-glass"
            aria-label="TourVoice Quận 4"
          >
            <img className="tv-brand-mark" src="/assets/tourvoice-mark.svg" width="30" height="30" alt="" />
            <span>
              <strong>TourVoice</strong>
              <small>Cẩm nang Quận 4</small>
            </span>
          </Link>

          {/* Desktop Search Bar (hidden on mobile, inline on desktop) */}
          <div className="tv-search-bar tv-glass tv-search-desktop" role="search">
            <Search size={17} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
            <input
              type="search"
              aria-label={tab === 'tours' ? ui.searchTours : ui.searchPlaces}
              placeholder={tab === 'tours' ? 'Tìm tuyến tour…' : 'Tìm quán ốc, phá lấu, di tích…'}
              value={query}
              onChange={event => searchCatalog(event.target.value)}
            />
            {query && (
              <button
                type="button"
                className="tv-search-clear"
                onClick={() => setQuery('')}
                aria-label="Xóa tìm kiếm"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {/* Top Actions & Badges (Always visible on mobile & desktop) */}
          <div className="tv-top-actions-group">
            {/* GPS Auto-Play Narration Switch */}
            <button
              type="button"
              className={`tv-hud-btn tv-glass ${autoPlay ? 'is-active tv-btn-autoplay-active' : ''}`}
              onClick={() => setAutoPlay(prev => !prev)}
              title={autoPlay ? 'Tự động phát GPS: BẬT' : 'Tự động phát GPS: TẮT'}
              aria-label={autoPlay ? 'Tắt tự động phát thuyết minh GPS' : 'Bật tự động phát thuyết minh GPS'}
              aria-pressed={autoPlay}
            >
              <Headphones size={17} aria-hidden="true" />
              <span className={`tv-pulse-dot ${autoPlay ? 'active' : ''}`} aria-hidden="true" />
            </button>

            {/* Language Switcher Pill (Guaranteed prominent visibility on mobile) */}
            <div className="tv-lang-pill tv-glass" title={ui.language}>
              <span className="tv-lang-flag" aria-hidden="true">{LANG_FLAGS[lang] || '🌐'}</span>
              <span className="tv-lang-code">{lang.toUpperCase()}</span>
              <ChevronDown size={13} className="tv-lang-arrow text-slate-400" aria-hidden="true" />
              <select
                className="tv-lang-select-hidden"
                aria-label={ui.language}
                value={lang}
                onChange={event => {
                  const next = event.target.value as SupportedLanguage;
                  setLang(next);
                  void setAppLanguage(next);
                  setDownloadText('');
                  closeRoute();
                }}
              >
                {languages.map(([code, label]) => (
                  <option key={code} value={code}>
                    {LANG_FLAGS[code] || ''} {label} ({code.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            {/* Account / Sign In */}
            <Link
              to={accountHref}
              className="tv-hud-btn tv-glass"
              aria-label={user ? ui.account : ui.signIn}
              title={user ? ui.account : ui.signIn}
            >
              <UserRound size={17} aria-hidden="true" />
            </Link>
          </div>
        </div>

        {/* Row 2: Mobile Full-Width Search Bar */}
        <div className="tv-hud-row-search">
          <div className="tv-search-bar tv-glass tv-search-mobile" role="search">
            <Search size={17} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
            <input
              type="search"
              aria-label={tab === 'tours' ? ui.searchTours : ui.searchPlaces}
              placeholder={tab === 'tours' ? 'Tìm tuyến tour…' : 'Tìm quán ốc, phá lấu, di tích…'}
              value={query}
              onChange={event => searchCatalog(event.target.value)}
            />
            {query && (
              <button
                type="button"
                className="tv-search-clear"
                onClick={() => setQuery('')}
                aria-label="Xóa tìm kiếm"
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Row 3: Category Filter Chips Bar */}
        {tab === 'places' && !selected && !tour && (
          <div className="tv-category-chips" role="toolbar" aria-label="Lọc nhanh danh mục ẩm thực">
            <button
              type="button"
              className="tv-chip tv-glass"
              aria-pressed={!category}
              onClick={() => setCategory('')}
            >
              <span>Tất cả</span>
            </button>
            {categories.map(value => (
              <button
                type="button"
                key={value}
                className="tv-chip tv-glass"
                aria-pressed={category === value}
                onClick={() => setCategory(value)}
              >
                <span>{value}</span>
              </button>
            ))}
          </div>
        )}
      </header>

      <aside className="tv-map-tools" aria-label="Thao tác bản đồ">
        <div className="tv-tool-group">
          <button type="button" className="tv-tool" onClick={() => setLayerModalOpen(true)}
            aria-label="Chọn kiểu bản đồ" aria-haspopup="dialog" aria-expanded={layerModalOpen}>
            <Layers size={18} aria-hidden="true" /><span>Bản đồ</span>
          </button>
          <button type="button" className="tv-tool tv-tool-location" onClick={() => void locate()}
            disabled={locating || routeBusy} aria-label="Định vị vị trí của tôi">
            <LocateFixed size={18} aria-hidden="true" /><span>{locating ? 'Đang tìm' : 'Vị trí tôi'}</span>
          </button>
        </div>
        <div className="tv-tool-group tv-tool-group-zoom">
          <button type="button" className="tv-tool" title="Phóng to" aria-label="Phóng to bản đồ"
            onClick={() => window.dispatchEvent(new CustomEvent('tourvoice:zoom', { detail: 1 }))}><Plus size={19} /></button>
          <button type="button" className="tv-tool" title="Thu nhỏ" aria-label="Thu nhỏ bản đồ"
            onClick={() => window.dispatchEvent(new CustomEvent('tourvoice:zoom', { detail: -1 }))}><Minus size={19} /></button>
          <button type="button" className="tv-tool" title="Về Quận 4" aria-label="Về trung tâm Quận 4"
            onClick={() => setAreaFocus(value => value + 1)}><Focus size={19} /></button>
          <button type="button" className="tv-tool tv-tool-dock" onClick={() => setDockOpen(prev => !prev)}
            title={dockOpen ? 'Ẩn danh sách' : 'Hiện danh sách'}
            aria-label={dockOpen ? 'Thu gọn bảng khám phá' : 'Mở bảng khám phá'}>
            {dockOpen ? <PanelLeftClose size={19} /> : <PanelLeftOpen size={19} />}
          </button>
        </div>
      </aside>
      {(pickOrigin || locating || gpsMessage || accuracy !== undefined || (routeBusy && snap === 'peek')) && (
        <div className="tv-location-status" role="status">
          <LocateFixed size={16} aria-hidden="true" />
          <span>{pickOrigin ? 'Chạm vào bản đồ để đặt điểm xuất phát.'
            : locating ? 'Đang tìm vị trí tốt nhất…'
            : routeBusy && snap === 'peek' ? routeMessage
            : gpsMessage || (accuracy !== undefined
              ? `${accuracy > ROUTE_ACCURACY ? 'Vị trí ước lượng' : 'Vị trí của bạn'} · Sai số khoảng ${Math.ceil(accuracy)} m`
              : '')}</span>
          {pickOrigin && <button type="button" onClick={closeRoute}>Hủy</button>}
        </div>
      )}

      {/* Tầng 4: Dynamic Island Audio Player (Floating when in Peek or Desktop) */}
      {narration.track && (
        <TouristPlayer key={narration.track.url} narration={narration} ui={ui}
          dock={dockOpen && snap !== 'peek' ? playerDock : null} />
      )}

      {/* Tầng 5: Left Floating Dock (Desktop) / Bottom Sheet (Mobile) (--z-sheet) */}
      <section
        className={`tv-sheet-dock tv-glass ${!dockOpen ? 'is-collapsed' : ''}`}
        data-snap={snap}
        ref={panel}
        role="region"
        aria-label="Bảng khám phá ẩm thực và tour Quận 4"
      >
        {/* Mobile Drag Handle & Toggle (Mục 1.2, 3) */}
        <button
          type="button"
          className="tv-sheet-handle-wrap"
          onClick={toggleSnap}
          aria-label="Chuyển kích thước bảng điều khiển"
          aria-expanded={snap !== 'peek'}
        >
          <span className="tv-sheet-handle" />
          <span className="tv-sheet-peek-summary">
            <span>{directions
              ? [directions.distance_display, directions.duration_display].filter(Boolean).join(' · ') || 'Sơ đồ lộ trình'
              : `Quận 4 · ${tab === 'places' ? `${visiblePlaces.length} điểm ẩm thực & di tích` : tab === 'tours' ? `${tours.length} tuyến tour` : `${offlinePacks.length} gói đã tải`}`}</span>
            <span className="text-orange-600 font-bold flex items-center gap-0.5">
              {snap === 'peek' ? 'Xem thêm' : 'Thu gọn'}
              {snap === 'peek' ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </span>
          </span>
        </button>

        {/* Dock Header: Segmented Tabs (Luôn nổi trên đầu Sheet / Dock để người dùng dễ chuyển đổi) */}
        {!selected && !tour && (
          <div className="tv-dock-header">
            <nav className="tv-tabs-segmented" aria-label="Chuyển chế độ xem">
              <button
                type="button"
                aria-pressed={tab === 'places'}
                onClick={() => {
                  switchTab('places');
                  if (snap === 'peek') setSnap('half');
                }}
              >
                <MapPin size={16} />
                <span>Quán ngon</span>
                <small>{visiblePlaces.length}</small>
              </button>
              <button
                type="button"
                aria-pressed={tab === 'tours'}
                onClick={() => {
                  switchTab('tours');
                  if (snap === 'peek') setSnap('half');
                }}
              >
                <Route size={16} />
                <span>Tuyến tour</span>
                <small>{tours.length}</small>
              </button>
              <button
                type="button"
                aria-pressed={tab === 'saved'}
                onClick={() => {
                  switchTab('saved');
                  if (snap === 'peek') setSnap('half');
                }}
              >
                <Download size={16} />
                <span>Đã lưu</span>
                <small>{offlinePacks.length}</small>
              </button>
            </nav>
          </div>
        )}

        {/* Mini Audio Player: gắn đỉnh sheet khi ở Half hoặc Full (Mục 1.3: Single Mobile Overlay Rule) */}
        <div ref={setPlayerDock} className="tv-player-dock" />

        {snap === 'peek' && (selected || tour) && (
          <div className="tv-peek-context">
            <MapPin size={19} aria-hidden="true" />
            <strong>{selected?.name || tour?.name}</strong>
            <button type="button" className="tv-btn-sheet-close" aria-label="Đóng chi tiết trên bản đồ" onClick={() => {
              setSelected(null);
              setTour(null);
              closeRoute();
            }}><X size={17} /></button>
          </div>
        )}

        {/* Mobile Peek State */}
        {snap === 'peek' && !selected && !tour && (
          <div className="tv-peek-carousel-wrap">
            <div className="tv-peek-carousel">
              {filteredPlaces.slice(0, 10).map(item => {
                const kind = categoryLabel(item.category);
                const distance = displayDistance(item);
                return (
                  <button
                    key={placeId(item)}
                    type="button"
                    className="tv-ticket-card-peek"
                    onClick={() => selectPlace(item)}
                  >
                    {distance && <span className="tv-distance-stamp">📍 Cách {distance}</span>}
                    <div className="tv-ticket-header">
                      <div className="tv-ticket-icon">
                        <Utensils size={17} />
                      </div>
                      <div className="min-w-0">
                        <small className="tv-card-kicker">{kind}</small>
                        <strong className="tv-ticket-title">{item.name}</strong>
                      </div>
                    </div>
                    <div className="tv-ticket-divider" />
                    <div className="tv-ticket-footer">
                      <span className="truncate">{item.address?.split(',')[0] || 'Quận 4, TP.HCM'}</span>
                      <span className="tv-ticket-cta">
                        Xem & Nghe <ChevronRight size={13} />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Dock Body: List or Details */}
        <div className="tv-dock-body">
          {(deepLinkError || failed) && (
            <div className="tv-menu-section" role="alert">
              <p>{deepLinkError || 'Chưa đồng bộ đủ địa điểm và tuyến tour.'}</p>
              {!deepLinkError && <button type="button" className="tv-btn-back" onClick={() => setReload(value => value + 1)}>Thử lại</button>}
            </div>
          )}
          {/* Offline Map Pack Storage Widget */}
          {tab === 'saved' && !tour && !selected && (
            <div className="tv-menu-section">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-sm font-bold flex items-center gap-1.5">
                  <Download size={16} className="text-orange-500" /> Bản đồ ngoại tuyến Quận 4
                </strong>
                <span className="text-xs text-slate-500 font-mono">
                  {mapPack.installed ? `${(mapPack.installed.manifest.size / 1_000_000).toFixed(1)} MB` : 'Chưa tải'}
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-3">
                {mapPack.installed
                  ? `Đã lưu bản đồ véc-tơ Quận 4 · Cập nhật ngày ${mapPack.installed.manifest.source_date}`
                  : 'Tải trước bản đồ để định vị và nghe thuyết minh mượt mà khi mất sóng 4G/5G.'}
              </p>
              <div className="flex gap-2">
                {online && (!mapPack.installed || mapPack.updateAvailable || mapPack.repairRequired) && (
                  <button
                    type="button"
                    className="tv-btn-action-primary text-xs !min-h-[36px] flex-1"
                    disabled={mapPack.busy}
                    onClick={() => void mapPack.install()}
                  >
                    <Download size={14} /> {mapPack.repairRequired ? 'Tải lại' : mapPack.updateAvailable ? 'Cập nhật' : 'Tải bản đồ'}
                  </button>
                )}
                {mapPack.installed && (
                  <button
                    type="button"
                    className="tv-btn-action-secondary text-xs !min-h-[36px]"
                    disabled={mapPack.busy}
                    onClick={() => void mapPack.remove()}
                  >
                    Xóa bản đồ
                  </button>
                )}
              </div>
              {mapPack.message && <p className="tv-checkout-message" role="status">{mapPack.message}</p>}
            </div>
          )}
          {tab === 'saved' && !tour && !selected && <AnalyticsConsent />}

          {/* Place List */}
          {tab === 'places' && !selected && !tour && (
            <>
              {loading && <div className="text-sm text-slate-500 py-6 text-center">Đang tải danh sách quán ngon & di tích…</div>}
              <ul className="tv-list">
                {filteredPlaces.map((item, index) => placeRow(item, index))}
              </ul>
              {!loading && !filteredPlaces.length && (
                <div className="text-center py-10 text-slate-500 text-sm">
                  Không tìm thấy điểm ẩm thực nào phù hợp từ khóa.
                </div>
              )}
            </>
          )}

          {/* Tours List */}
          {tab === 'tours' && !selected && !tour && (
            <ul className="tv-list">
              {browseTours.map(item => (
                <li key={placeId(item)}>
                  <button
                    type="button"
                    className="tv-card-item"
                    onClick={() => selectTour(item)}
                  >
                    <span className="tv-card-icon" aria-hidden="true">
                      <Route size={20} />
                    </span>
                    <span className="tv-card-text">
                      <small className="tv-card-kicker">Tuyến tham quan</small>
                      <strong>{tourTitle(item)}</strong>
                      <small>
                        {item.poi_count ?? item.stops?.length ?? 0} điểm dừng ·{' '}
                        {offlinePacks.some(pack => pack.tour_id === placeId(item))
                          ? 'Đã tải ngoại tuyến'
                          : item.price_amount
                          ? formatVnd(item.price_amount)
                          : 'Miễn phí'}
                      </small>
                    </span>
                    <ChevronRight size={18} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Saved Offline Packs */}
          {tab === 'saved' && !selected && !tour && (
            <ul className="tv-list">
              {browsePacks.map(pack => (
                <li key={pack.tour_id}>
                  <button
                    type="button"
                    className="tv-card-item"
                    onClick={() => selectTour({ id: pack.tour_id, name: pack.tour_name, pois: pack.pois })}
                  >
                    <span className="tv-card-icon" aria-hidden="true">
                      <Download size={20} />
                    </span>
                    <span className="tv-card-text">
                      <small className="tv-card-kicker">Đã tải về máy</small>
                      <strong>{pack.tour_name}</strong>
                      <small>{pack.pois.length} điểm thuyết minh</small>
                    </span>
                    <ChevronRight size={18} className="text-slate-400 flex-shrink-0" aria-hidden="true" />
                  </button>
                </li>
              ))}
              {!offlinePacks.length && (
                <div className="text-center py-10 text-slate-500 text-sm">
                  Chưa có tuyến tour nào được tải ngoại tuyến.
                </div>
              )}
            </ul>
          )}

          {/* Detail View: Selected Place (Signature Ticket Card Motif) */}
          {selected && (
            <article className="tv-detail-view" aria-label="Chi tiết địa điểm">
              <div className="tv-detail-header-row">
                <button
                  type="button"
                  className="tv-btn-back"
                  onClick={() => {
                    setSelected(null);
                    closeRoute();
                  }}
                >
                  <ChevronLeft size={16} /> {tour ? 'Về tuyến tour' : 'Về danh sách'}
                </button>
                <button
                  type="button"
                  className="tv-btn-sheet-close"
                  onClick={() => {
                    setSelected(null);
                    closeRoute();
                    setSnap('peek');
                  }}
                  aria-label="Đóng chi tiết"
                >
                  <X size={17} />
                </button>
              </div>

              <div>
                <span className="tv-card-kicker">{categoryLabel(selected.category)}</span>
                <h2 className="tv-detail-title">{selected.name}</h2>
                {selected.address && (
                  <p className="tv-detail-address">
                    <MapPin size={15} className="text-orange-500 flex-shrink-0" />
                    <span>{selected.address}</span>
                  </p>
                )}
              </div>

              {/* Action Buttons: Listen & Directions */}
              <div className="tv-detail-actions">
                <button
                  type="button"
                  className="tv-btn-action-primary"
                  disabled={audioDisabled}
                  onClick={() => playPlace(selected)}
                >
                  <Headphones size={18} />
                  <span>{narration.busy ? ui.preparing : 'Nghe thuyết minh ngay'}</span>
                </button>
                {online && (
                  <button
                    type="button"
                    className="tv-btn-action-secondary"
                    disabled={routeBusy || locating}
                    onClick={() => void showRoute(selected)}
                  >
                    <Route size={18} className="text-orange-500" />
                    <span>{routeBusy ? 'Đang tìm đường…' : 'Chỉ đường'}</span>
                  </button>
                )}
              </div>

              {online && <button type="button" className="tv-origin-action" onClick={() => {
                closeRoute();
                setPickOrigin(selected);
                setSnap('peek');
              }}><MapPin size={15} aria-hidden="true" /> Chọn điểm xuất phát trên bản đồ</button>}

              {/* Audio Locale / Fallback Notice */}
              {(selected.is_fallback ||
                (selected.narration_ready === false && (online || !offlineAudioIds.has(placeId(selected))))) && (
                <div className="p-3 bg-orange-50 border border-orange-200 rounded-xl text-xs text-orange-900 flex flex-col gap-2">
                  <span>
                    {selected.narration_ready === false
                      ? online ? 'Điểm này chưa có bản thu. Bấm nghe để tạo giọng đọc tự động.' : 'Điểm này chưa có thuyết minh tải về.'
                      : `Nội dung phát bằng ${languages.find(([code]) => code === selected.resolved_lang)?.[1] || selected.resolved_lang}.`}
                  </span>
                  {online && (
                    <button
                      type="button"
                      className="font-bold underline text-left"
                      disabled={preparation?.busy}
                      onClick={() => void prepareLocale(selected)}
                    >
                      Khởi tạo bản dịch {languages.find(([code]) => code === lang)?.[1] || lang}
                    </button>
                  )}
                </div>
              )}

              {preparation && <p className="text-xs text-slate-500">{preparation.text}</p>}

              {selected.description && <p className="tv-detail-desc">{selected.description}</p>}

              {/* Food Menu Dropdown */}
              {!!menu.length && (
                <details className="tv-menu-section" open>
                  <summary className="tv-menu-summary flex items-center justify-between">
                    <span>Thực đơn đặc sản ({menu.length} món)</span>
                    <ChevronDown size={16} />
                  </summary>
                  <ul className="tv-menu-list">
                    {menu.map(item => (
                      <li key={item.id || item._id || item.name}>
                        <span>{item.name}</span>
                        {Number(item.price_amount || item.price) > 0 && (
                          <span className="tv-menu-price">{formatVnd(Number(item.price_amount || item.price))}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </article>
          )}

          {/* Detail View: Selected Tour */}
          {tour && !selected && (
            <article className="tv-detail-view" aria-label="Chi tiết tuyến tham quan">
              <div className="tv-detail-header-row">
                <button
                  type="button"
                  className="tv-btn-back"
                  onClick={() => {
                    setTour(null);
                    closeRoute();
                  }}
                >
                  <ChevronLeft size={16} /> {tab === 'saved' ? 'Về gói đã lưu' : 'Tất cả tuyến tour'}
                </button>
                <button
                  type="button"
                  className="tv-btn-sheet-close"
                  onClick={() => {
                    setTour(null);
                    closeRoute();
                    setSnap('peek');
                  }}
                  aria-label="Đóng chi tiết tour"
                >
                  <X size={17} />
                </button>
              </div>

              <div>
                <span className="tv-card-kicker">
                  {access?.has_entitlement ? 'Đã sở hữu vé' : paid ? formatVnd(price) : 'Miễn phí'}
                </span>
                <h2 className="tv-detail-title">{tourTitle(tour)}</h2>
              </div>

              {(tour.localizations?.[lang]?.description || tour.description) && (
                <p className="tv-detail-desc">{tour.localizations?.[lang]?.description || tour.description}</p>
              )}

              {/* Tour Actions */}
              <div className="flex flex-wrap gap-2">
                {online && tourPlaces.length > 1 && (
                  <button
                    type="button"
                    className="tv-btn-action-primary flex-1 !min-h-[44px]"
                    disabled={routeBusy}
                    onClick={() => void showRoute()}
                  >
                    <Route size={17} /> {routeBusy ? 'Đang tìm lộ trình…' : 'Xem lộ trình'}
                  </button>
                )}
                {online && access?.can_download && (
                  <button
                    type="button"
                    className="tv-btn-action-secondary flex-1 !min-h-[44px]"
                    disabled={downloading}
                    onClick={() => void download()}
                  >
                    <Download size={16} /> {packSaved ? 'Cập nhật' : 'Tải gói'}
                  </button>
                )}
                {packSaved && (
                  <button
                    type="button"
                    className="text-xs text-red-600 underline font-semibold self-center"
                    disabled={downloading}
                    onClick={() => void remove()}
                  >
                    Xóa gói
                  </button>
                )}
              </div>

              {downloadText && <p className="text-xs text-orange-600">{downloadText}</p>}
              {tourError && <p className="text-xs text-red-600">{tourError}</p>}
              {receipt && receipt.tourId === tourId && receipt.userId === user?.id && (
                <div className="tv-checkout-success" role="status">
                  <CheckCircle2 size={19} aria-hidden="true" />
                  <div>
                    <strong>{receipt.order.simulated ? 'Thanh toán mô phỏng thành công' : 'Thanh toán thành công'}</strong>
                    {receipt.order.ticket_code && <small>Mã vé {receipt.order.ticket_code}</small>}
                  </div>
                </div>
              )}

              {/* Paid tour checkout */}
              {online && access && paid && !access.has_entitlement && tour.is_purchasable !== false && (
                <div className="mt-2">
                  {user ? (
                    <TouristCheckout
                      key={user.id + ':' + tourId}
                      tourId={tourId!}
                      price={price}
                      user={user}
                      onPaid={order => {
                        setReceipt({ tourId: tourId!, userId: user.id, order });
                        setAccessRevision(value => value + 1);
                      }}
                    />
                  ) : (
                    <Link
                      className="tv-btn-action-primary w-full text-center"
                      to={{ pathname: accountHref, search: '?tour=' + idPath(tourId!) }}
                    >
                      Đăng nhập để mua vé tour
                    </Link>
                  )}
                </div>
              )}

              {/* Stops in Tour */}
              <div className="mt-3">
                <h3 className="text-sm font-bold text-slate-800 mb-2 flex items-center gap-1.5">
                  <BookOpen size={16} className="text-orange-500" /> Các điểm dừng theo lộ trình ({tourPlaces.length})
                </h3>
                {tourPlaces.length ? (
                  <ol className="tv-list">
                    {tourPlaces.map((item, index) => placeRow(item, index, true))}
                  </ol>
                ) : (
                  <p className="text-xs text-slate-500">Chưa có điểm dừng nào trong tour này.</p>
                )}
              </div>
            </article>
          )}

          {/* Walking Directions Panel */}
          {directions && (
            <div className="tv-menu-section mt-2">
              <div className="flex items-center justify-between mb-2">
                <strong className="text-sm font-bold text-orange-600 flex items-center gap-1.5">
                  <Route size={16} />{' '}
                  {directions.approximate
                    ? 'Sơ đồ điểm dừng'
                    : [directions.distance_display, directions.duration_display].filter(Boolean).join(' · ') ||
                      'Chỉ dẫn đường đi'}
                </strong>
                <button
                  type="button"
                  className="text-xs font-bold text-slate-500 hover:text-slate-800"
                  onClick={closeRoute}
                  aria-label="Ẩn lộ trình"
                >
                  Đóng
                </button>
              </div>
              <ol className="text-xs text-slate-700 space-y-1.5 pl-4 list-decimal">
                {directions.steps?.map((step, index) => (
                  <li key={index}>{step.instruction}</li>
                ))}
              </ol>
            </div>
          )}

          {routeMessage && <p className="tv-route-status" role="status">{routeMessage}</p>}
          {audioError && <p className="text-xs text-red-600 mt-2">{audioError}</p>}
        </div>
      </section>

      {/* Modal Dialog: Trial & Entitlement (--z-modal) */}
      {(narration.trial || narration.gateReason) && (
        <NarrationDialog
          trialPlace={narration.trial?.place.name}
          reason={narration.gateReason}
          onDismiss={narration.trial ? narration.decline : narration.dismissGate}
          onConfirm={() => {
            if (narration.trial) {
              void narration.play({ ...narration.trial, consent: true });
            } else {
              const id = narration.gateTourId;
              const target = tourId === id ? tour : tours.find(item => placeId(item) === id);
              narration.dismissGate();
              selectTour(target || { id, name: '' });
              if (tourId === id) setAccessRevision(value => value + 1);
            }
          }}
        />
      )}

      {/* Basemap Selection Modal */}
      <BasemapSelector
        open={layerModalOpen}
        onClose={() => setLayerModalOpen(false)}
        currentMode={mapPack.mode}
        online={online}
        onSelectMode={mapPack.changeMode}
        installedPack={mapPack.installed}
      />
    </div>
  );
}
