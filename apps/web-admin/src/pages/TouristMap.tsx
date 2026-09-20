import React, { useEffect, useState, useRef } from 'react';
import { 
  MapPin, 
  Navigation, 
  Volume2, 
  VolumeX, 
  Play, 
  Pause, 
  Globe, 
  Lock, 
  User, 
  LogIn, 
  UserPlus, 
  Compass, 
  CheckCircle2, 
  Headphones, 
  Radio,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Search,
  Route,
  X,
  Footprints,
  Car,
  Bike,
  CornerDownRight,
  Navigation2
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';
import { tourService, Tour } from '../services/tourService';

// Multi-language dictionary
type LangCode = 'vi' | 'en' | 'fr' | 'ja' | 'ko' | 'zh';

const I18N: Record<LangCode, {
  name: string;
  flag: string;
  authRequiredTitle: string;
  authRequiredDesc: string;
  loginTab: string;
  registerTab: string;
  guestBtn: string;
  emailLabel: string;
  passLabel: string;
  nameLabel: string;
  loginBtn: string;
  registerBtn: string;
  gpsActive: string;
  gpsWaiting: string;
  locateMe: string;
  poisNearby: string;
  distanceLabel: string;
  listenNarration: string;
  autoAudioOn: string;
  autoAudioOff: string;
  switchLang: string;
  sightseeing: string;
  historical: string;
  food: string;
  culture: string;
}> = {
  vi: {
    name: 'Tiếng Việt',
    flag: '🇻🇳',
    authRequiredTitle: 'Chào Mừng Đến Với Quận 4!',
    authRequiredDesc: 'Vui lòng đăng nhập hoặc đăng ký tài khoản để kích hoạt hệ thống thuyết minh GPS tự động và khám phá di tích Quận 4.',
    loginTab: 'Đăng Nhập',
    registerTab: 'Đăng Ký',
    guestBtn: 'Trải Nghiệm Nhanh Với Tư Cách Khách',
    emailLabel: 'Địa chỉ Email',
    passLabel: 'Mật khẩu',
    nameLabel: 'Họ và tên',
    loginBtn: 'Đăng Nhập Vào Hệ Thống',
    registerBtn: 'Tạo Tài Khoản Mới',
    gpsActive: 'GPS Đang Hoạt Động (Thời Gian Thực)',
    gpsWaiting: 'Đang tìm kiếm tín hiệu GPS...',
    locateMe: 'Vị Trí Của Tôi',
    poisNearby: 'Các Điểm Thuyết Minh Quận 4',
    distanceLabel: 'Cách bạn',
    listenNarration: 'Nghe Thuyết Minh',
    autoAudioOn: 'Tự động phát khi đến gần: BẬT',
    autoAudioOff: 'Tự động phát khi đến gần: TẮT',
    switchLang: 'Chọn Ngôn Ngữ',
    sightseeing: 'Cảnh quan',
    historical: 'Di tích lịch sử',
    food: 'Ẩm thực',
    culture: 'Văn hóa'
  },
  en: {
    name: 'English',
    flag: '🇬🇧',
    authRequiredTitle: 'Welcome to District 4 TourVoice!',
    authRequiredDesc: 'Please sign in or register to enable automated GPS audio narration and explore historical attractions of District 4.',
    loginTab: 'Sign In',
    registerTab: 'Register',
    guestBtn: 'Quick Tourist Guest Access',
    emailLabel: 'Email Address',
    passLabel: 'Password',
    nameLabel: 'Full Name',
    loginBtn: 'Sign In',
    registerBtn: 'Create Account',
    gpsActive: 'Live GPS Tracking Active',
    gpsWaiting: 'Acquiring GPS Signal...',
    locateMe: 'Locate Me',
    poisNearby: 'District 4 Narration Points',
    distanceLabel: 'Distance',
    listenNarration: 'Play Audio Narration',
    autoAudioOn: 'Auto Play on Proximity: ON',
    autoAudioOff: 'Auto Play on Proximity: OFF',
    switchLang: 'Language',
    sightseeing: 'Sightseeing',
    historical: 'Historical',
    food: 'Food & Culinary',
    culture: 'Culture'
  },
  fr: {
    name: 'Français',
    flag: '🇫🇷',
    authRequiredTitle: 'Bienvenue au District 4 TourVoice!',
    authRequiredDesc: 'Veuillez vous connecter ou vous inscrire pour activer la narration GPS automatique.',
    loginTab: 'Connexion',
    registerTab: 'Inscription',
    guestBtn: 'Accès Rapide Invité',
    emailLabel: 'Adresse e-mail',
    passLabel: 'Mot de passe',
    nameLabel: 'Nom complet',
    loginBtn: 'Se Connecter',
    registerBtn: 'Créer un Compte',
    gpsActive: 'GPS en Direct Actif',
    gpsWaiting: 'Recherche du Signal GPS...',
    locateMe: 'Ma Position',
    poisNearby: 'Sites Narratifs du District 4',
    distanceLabel: 'Distance',
    listenNarration: 'Écouter la Narration',
    autoAudioOn: 'Lecture Auto Proximité: OUI',
    autoAudioOff: 'Lecture Auto Proximité: NON',
    switchLang: 'Langue',
    sightseeing: 'Tourisme',
    historical: 'Historique',
    food: 'Gastronomie',
    culture: 'Culture'
  },
  ja: {
    name: '日本語',
    flag: '🇯🇵',
    authRequiredTitle: '第4区オーディオガイドへようこそ！',
    authRequiredDesc: 'GPS自動音声案内を有効にするには、ログインまたは新規登録してください。',
    loginTab: 'ログイン',
    registerTab: '新規登録',
    guestBtn: 'ゲストとして今すぐ体験',
    emailLabel: 'メールアドレス',
    passLabel: 'パスワード',
    nameLabel: 'お名前',
    loginBtn: 'ログイン',
    registerBtn: 'アカウント作成',
    gpsActive: 'GPS追跡が有効です',
    gpsWaiting: 'GPS信号を取得中...',
    locateMe: '現在地',
    poisNearby: '第4区の案内スポット',
    distanceLabel: '距離',
    listenNarration: '音声ガイドを聞く',
    autoAudioOn: '接近時自動再生: オン',
    autoAudioOff: '接近時自動再生: オフ',
    switchLang: '言語選択',
    sightseeing: '観光地',
    historical: '歴史的遺跡',
    food: 'グルメ',
    culture: '文化'
  },
  ko: {
    name: '한국어',
    flag: '🇰🇷',
    authRequiredTitle: '4군 오디오 투어가이드에 오신 것을 환영합니다!',
    authRequiredDesc: 'GPS 자동 안내 음성을 이용하시려면 로그인 또는 회원가입을 진행해 주세요.',
    loginTab: '로그인',
    registerTab: '회원가입',
    guestBtn: '게스트로 즉시 체험',
    emailLabel: '이메일 주소',
    passLabel: '비밀번호',
    nameLabel: '성명',
    loginBtn: '로그인',
    registerBtn: '회원가입 완료',
    gpsActive: '실시간 GPS 활성화됨',
    gpsWaiting: 'GPS 신호 검색 중...',
    locateMe: '내 위치 찾기',
    poisNearby: '4군 추천 명소',
    distanceLabel: '거리',
    listenNarration: '해설 듣기',
    autoAudioOn: '근접 시 자동 재생: 켬',
    autoAudioOff: '근접 시 자동 재생: 끔',
    switchLang: '언어 변경',
    sightseeing: '관광 명소',
    historical: '역사 유적',
    food: '음식 및 맛집',
    culture: '문화'
  },
  zh: {
    name: '中文',
    flag: '🇨🇳',
    authRequiredTitle: '欢迎来到第四郡智能导览！',
    authRequiredDesc: '请登录或注册以开启GPS智能语音讲解系统。',
    loginTab: '登录',
    registerTab: '注册',
    guestBtn: '游客快速体验',
    emailLabel: '电子邮箱',
    passLabel: '密码',
    nameLabel: '姓名',
    loginBtn: '立即登录',
    registerBtn: '注册账号',
    gpsActive: '实时GPS定位已开启',
    gpsWaiting: '正在搜索GPS信号...',
    locateMe: '我的位置',
    poisNearby: '第四郡景点与导览点',
    distanceLabel: '距离',
    listenNarration: '播放语音讲解',
    autoAudioOn: '靠近自动播放: 开启',
    autoAudioOff: '靠近自动播放: 关闭',
    switchLang: '选择语言',
    sightseeing: '观光景点',
    historical: '历史遗迹',
    food: '特色美食',
    culture: '文化宗教'
  }
};

// Haversine formula to compute distance in meters
function calculateDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

export const TouristMap: React.FC = () => {
  const { user, token, login } = useAuth();
  const [searchParams] = useSearchParams();

  // Multi-language State
  const [lang, setLang] = useState<LangCode>('vi');
  const t = I18N[lang];

  // Auth Gate Modal State (Defaults to false so guests can freely explore)
  const [showAuthGate, setShowAuthGate] = useState(false);
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Tours State
  const [tours, setTours] = useState<Tour[]>([]);
  const [activeTour, setActiveTour] = useState<Tour | null>(null);
  const [showToursModal, setShowToursModal] = useState(false);
  const [tourLoading, setTourLoading] = useState(false);
  const tourPolylineRef = useRef<any>(null);
  const tourStopMarkersRef = useRef<any[]>([]);

  // GPS Simulation Demo State
  const [isSimulatingGps, setIsSimulatingGps] = useState(false);
  const isSimulatingGpsRef = useRef(false);
  useEffect(() => {
    isSimulatingGpsRef.current = isSimulatingGps;
  }, [isSimulatingGps]);

  // POIs and Live GPS State
  const [pois, setPois] = useState<any[]>([]);
  const [currentLat, setCurrentLat] = useState<number>(10.7635);
  const [currentLng, setCurrentLng] = useState<number>(106.7042);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [hasRealGps, setHasRealGps] = useState(false);

  // Active Audio Narration State
  const [activePoi, setActivePoi] = useState<any | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(true);
  const [playedPoiIds, setPlayedPoiIds] = useState<Set<string>>(new Set());
  const [playerMinimized, setPlayerMinimized] = useState(false);

  // Mobile POI Drawer State
  const [showMobilePoiList, setShowMobilePoiList] = useState(false);
  const [mobilePoiSearch, setMobilePoiSearch] = useState('');

  // Refs for Map and Audio
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const userMarkerRef = useRef<any>(null);
  const accuracyCircleRef = useRef<any>(null);
  const poiMarkersRef = useRef<any[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Routing & Directions State
  const [showRouteModal, setShowRouteModal] = useState(false);
  const [routeOriginType, setRouteOriginType] = useState<'my_location' | 'poi'>('my_location');
  const [routeOriginPoiId, setRouteOriginPoiId] = useState<string>('');
  const [routeDestPoiId, setRouteDestPoiId] = useState<string>('');
  const [routeMode, setRouteMode] = useState<'walking' | 'driving' | 'cycling'>('walking');
  const [currentRoute, setCurrentRoute] = useState<any | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [showTurnByTurn, setShowTurnByTurn] = useState(false);
  const routePolylineRef = useRef<any>(null);

  const calculateRoute = async (
    originMode: 'my_location' | 'poi',
    origPoiId: string,
    destPoiId: string,
    mode: 'walking' | 'driving' | 'cycling' = 'walking'
  ) => {
    if (!destPoiId) {
      alert('Vui lòng chọn địa điểm đến.');
      return;
    }
    if (originMode === 'poi' && !origPoiId) {
      alert('Vui lòng chọn địa điểm xuất phát.');
      return;
    }
    if (originMode === 'poi' && origPoiId === destPoiId) {
      alert('Điểm xuất phát và điểm đến không được trùng nhau.');
      return;
    }

    setRouteLoading(true);
    try {
      const payload: any = {
        mode,
        locale: lang
      };
      if (originMode === 'my_location') {
        payload.origin = { latitude: currentLat, longitude: currentLng };
      } else {
        payload.origin_poi_id = origPoiId;
      }
      payload.destination_poi_id = destPoiId;

      const res = await fetch(apiUrl('/routes/preview'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const routeData = await res.json();
        setCurrentRoute(routeData);

        // Draw Polyline on Leaflet Map
        const L = (window as any).L;
        if (L && mapInstanceRef.current && routeData.coordinates) {
          if (routePolylineRef.current) {
            routePolylineRef.current.remove();
          }
          const latLngs = routeData.coordinates.map(([lon, lat]: [number, number]) => [lat, lon]);
          routePolylineRef.current = L.polyline(latLngs, {
            color: '#0284c7',
            weight: 6,
            opacity: 0.9,
            lineJoin: 'round'
          }).addTo(mapInstanceRef.current);

          mapInstanceRef.current.fitBounds(routePolylineRef.current.getBounds(), {
            padding: [60, 60]
          });
        }
        setShowRouteModal(false);
      } else {
        alert('Không thể tính toán tuyến đường: Vui lòng kiểm tra lại điểm xuất phát và điểm đến.');
      }
    } catch (e: any) {
      console.error('Route calculation error:', e);
      alert('Lỗi tính toán đường đi: ' + e.message);
    } finally {
      setRouteLoading(false);
    }
  };

  const clearRoute = () => {
    setCurrentRoute(null);
    setShowTurnByTurn(false);
    if (routePolylineRef.current) {
      routePolylineRef.current.remove();
      routePolylineRef.current = null;
    }
  };

  const routeToPoi = (targetPoi: any) => {
    const pid = targetPoi.id || targetPoi._id;
    setRouteDestPoiId(pid);
    setRouteOriginType('my_location');
    calculateRoute('my_location', '', pid, routeMode);
  };

  // 1. Authentication Gate (Tourists explore freely; only close modal when signed in)
  useEffect(() => {
    if (user) {
      setShowAuthGate(false);
    }
  }, [user]);

  // Fetch available tours
  const fetchTours = async () => {
    try {
      const data = await tourService.getTours();
      setTours(data);
    } catch (err) {
      console.error('Fetch tours error:', err);
    }
  };

  useEffect(() => {
    fetchTours();
  }, []);

  const selectTour = async (tourId: string) => {
    setTourLoading(true);
    try {
      const tourData = await tourService.getTourDetail(tourId, lang);
      setActiveTour(tourData);
      setShowToursModal(false);

      const L = (window as any).L;
      if (L && mapInstanceRef.current) {
        // Clear previous tour markers & route
        if (tourPolylineRef.current) {
          tourPolylineRef.current.remove();
          tourPolylineRef.current = null;
        }
        tourStopMarkersRef.current.forEach((m) => m.remove());
        tourStopMarkersRef.current = [];

        const validPois = (tourData.pois || []).filter((p: any) => p.location?.coordinates);
        if (validPois.length > 0) {
          const latLngs = validPois.map((p: any) => [p.location.coordinates[1], p.location.coordinates[0]]);
          tourPolylineRef.current = L.polyline(latLngs, {
            color: '#6366f1',
            weight: 5,
            opacity: 0.9,
            dashArray: '10, 8',
            lineJoin: 'round'
          }).addTo(mapInstanceRef.current);

          mapInstanceRef.current.fitBounds(tourPolylineRef.current.getBounds(), {
            padding: [80, 80]
          });

          // Draw ordered stop numbers
          validPois.forEach((p: any, idx: number) => {
            const [lon, lat] = p.location.coordinates;
            const stopIcon = L.divIcon({
              className: 'tour-stop-pin',
              html: `
                <div style="background: #4f46e5; color: white; border: 2.5px solid #ffffff; border-radius: 9999px; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.6);">
                  ${idx + 1}
                </div>
              `,
              iconSize: [30, 30],
              iconAnchor: [15, 15]
            });
            const marker = L.marker([lat, lon], { icon: stopIcon, zIndexOffset: 800 }).addTo(mapInstanceRef.current);
            marker.bindPopup(`<b>Điểm dừng ${idx + 1}: ${p.name}</b><p style="font-size: 11px; margin: 2px 0;">${p.address || ''}</p>`);
            marker.on('click', () => {
              setActivePoi(p);
            });
            tourStopMarkersRef.current.push(marker);
          });

          // Set active POI to stop 1
          setActivePoi(validPois[0]);
        }
      }
    } catch (err: any) {
      console.error('Select tour error:', err);
    } finally {
      setTourLoading(false);
    }
  };

  const clearActiveTour = () => {
    setActiveTour(null);
    if (tourPolylineRef.current) {
      tourPolylineRef.current.remove();
      tourPolylineRef.current = null;
    }
    tourStopMarkersRef.current.forEach((m) => m.remove());
    tourStopMarkersRef.current = [];
  };

  const simulateMoveToPoi = (targetPoi: any) => {
    if (!targetPoi?.location?.coordinates) return;
    const [lon, lat] = targetPoi.location.coordinates;
    setIsSimulatingGps(true);
    setCurrentLat(lat);
    setCurrentLng(lon);
    setHasRealGps(true);
    if (userMarkerRef.current) {
      userMarkerRef.current.setLatLng([lat, lon]);
    }
    if (accuracyCircleRef.current) {
      accuracyCircleRef.current.setLatLng([lat, lon]);
    }
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lat, lon], 17);
    }
  };

  // Handle URL deep-linking (?type=tour&id=... or ?type=poi&id=... or ?tour=... or ?poi=... or ?qr=...)
  useEffect(() => {
    const handleUrlParams = async () => {
      const qType = searchParams.get('type');
      const qId = searchParams.get('id');
      const qTour = searchParams.get('tour');
      const qPoi = searchParams.get('poi');
      const qQr = searchParams.get('qr');

      // 1. Tour parameter directly
      const targetTourId = qTour || (qType === 'tour' ? qId : null);
      if (targetTourId) {
        selectTour(targetTourId);
        return;
      }

      // 2. POI parameter directly
      const targetPoiId = qPoi || (qType === 'poi' ? qId : null);
      if (targetPoiId) {
        try {
          const res = await fetch(apiUrl(`/pois/${targetPoiId}?lang=${lang}`));
          if (res.ok) {
            const poiData = await res.json();
            setActivePoi(poiData);
            if (mapInstanceRef.current && poiData.location?.coordinates) {
              const [lon, lat] = poiData.location.coordinates;
              mapInstanceRef.current.setView([lat, lon], 17);
            }
            playAudio(poiData);
          }
        } catch (e) {
          console.error('Error loading deep-linked POI:', e);
        }
        return;
      }

      // 3. QR code string
      if (qQr) {
        try {
          const res = await fetch(apiUrl(`/qr/${encodeURIComponent(qQr)}`));
          if (res.ok) {
            const qrData = await res.json();
            if ((qrData.target_type === 'tour' || qrData.tour) && (qrData.tour_id || qrData.tour?.id)) {
              selectTour(qrData.tour_id || qrData.tour.id);
            } else if (qrData.poi) {
              setActivePoi(qrData.poi);
              if (mapInstanceRef.current && qrData.poi.location?.coordinates) {
                const [lon, lat] = qrData.poi.location.coordinates;
                mapInstanceRef.current.setView([lat, lon], 17);
              }
              playAudio(qrData.poi);
            }
          }
        } catch (e) {
          console.error('Error resolving QR code from URL:', e);
        }
      }
    };

    handleUrlParams();
  }, [searchParams]);

  // Helper to extract localized POI name
  const getPoiName = (p: any, langCode: LangCode = lang) => {
    if (!p) return '';
    return p.translations?.[langCode]?.name || p.published_contents?.[langCode]?.name || p.published_contents?.[langCode]?.title || p.name || p.title || 'Điểm tham quan';
  };

  // Helper to extract localized POI description
  const getPoiDesc = (p: any, langCode: LangCode = lang) => {
    if (!p) return '';
    return p.translations?.[langCode]?.description || p.published_contents?.[langCode]?.description || p.description || '';
  };

  // 2. Fetch POIs with language support
  const fetchPOIs = async (langCode: LangCode) => {
    try {
      const res = await fetch(apiUrl(`/pois?limit=50&lang=${langCode}`));
      if (res.ok) {
        const data = await res.json();
        const items = data.items || [];
        setPois(items);
        if (items.length > 0) {
          setActivePoi((prev: any) => {
            if (!prev) return items[0];
            const updated = items.find((p: any) => (p.id || p._id) === (prev.id || prev._id));
            return updated || items[0];
          });
        }
      }
    } catch (err) {
      console.error('Fetch tourist POIs error:', err);
    }
  };

  useEffect(() => {
    fetchPOIs(lang);
  }, [lang]);

  // 3. Initialize Live GPS Watch
  useEffect(() => {
    if (!navigator.geolocation) return;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCurrentLat(lat);
        setCurrentLng(lng);
        setAccuracy(Math.round(pos.coords.accuracy));
        setHasRealGps(true);

        // Update user marker on map
        if (mapInstanceRef.current && (window as any).L) {
          const L = (window as any).L;
          if (userMarkerRef.current) {
            userMarkerRef.current.setLatLng([lat, lng]);
          }
          if (accuracyCircleRef.current) {
            accuracyCircleRef.current.setLatLng([lat, lng]);
            accuracyCircleRef.current.setRadius(pos.coords.accuracy);
          }
        }
      },
      (err) => {
        console.warn('Live GPS watch error:', err);
      },
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 10000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  // 4. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    const L = (window as any).L;
    if (!L) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current).setView([currentLat, currentLng], 15);

      // Google Maps Road Map layer (Rõ nét, chuẩn Google Maps)
      const roadLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        attribution: '© Google Maps',
        maxZoom: 20
      });

      // Google Maps Satellite Hybrid layer (Ảnh vệ tinh có tên đường)
      const satelliteLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        attribution: '© Google Maps (Vệ tinh)',
        maxZoom: 20
      });

      roadLayer.addTo(map);

      // Add layer control
      L.control.layers({
        'Bản Đồ Google': roadLayer,
        'Ảnh Vệ Tinh': satelliteLayer
      }, undefined, { position: 'topright' }).addTo(map);

      // Custom pulsing user GPS marker
      const userIcon = L.divIcon({
        className: 'custom-user-marker',
        html: `
          <div style="position: relative; width: 22px; height: 22px;">
            <div style="position: absolute; width: 22px; height: 22px; border-radius: 50%; background: #3b82f6; opacity: 0.4; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
            <div style="position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #2563eb; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
          </div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      userMarkerRef.current = L.marker([currentLat, currentLng], { icon: userIcon }).addTo(map);
      accuracyCircleRef.current = L.circle([currentLat, currentLng], {
        radius: accuracy || 25,
        color: '#3b82f6',
        fillColor: '#60a5fa',
        fillOpacity: 0.15,
        weight: 1
      }).addTo(map);

      // GPS simulation click listener
      map.on('click', (e: any) => {
        if (isSimulatingGpsRef.current) {
          const { lat, lng } = e.latlng;
          setCurrentLat(lat);
          setCurrentLng(lng);
          setHasRealGps(true);
          if (userMarkerRef.current) {
            userMarkerRef.current.setLatLng([lat, lng]);
          }
          if (accuracyCircleRef.current) {
            accuracyCircleRef.current.setLatLng([lat, lng]);
          }
        }
      });

      mapInstanceRef.current = map;
    }
  }, []);

  // 5. Render POI Markers on Map
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const L = (window as any).L;
    if (!L) return;

    // Clear old POI markers
    poiMarkersRef.current.forEach((m) => m.remove());
    poiMarkersRef.current = [];

    pois.forEach((p) => {
      const coords = p.location?.coordinates;
      if (!coords) return;
      const [lon, lat] = coords;
      const poiTitle = getPoiName(p, lang);

      const poiIcon = L.divIcon({
        className: 'custom-poi-marker',
        html: `
          <div style="background: ${activePoi?.id === p.id ? '#6366f1' : '#0f172a'}; color: white; padding: 6px; border-radius: 12px; border: 2px solid ${activePoi?.id === p.id ? '#a5b4fc' : '#334155'}; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; width: 34px; height: 34px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
          </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 34]
      });

      const marker = L.marker([lat, lon], { icon: poiIcon }).addTo(mapInstanceRef.current);
      marker.bindPopup(`
        <div style="font-family: sans-serif; min-width: 160px;">
          <b style="color: #0f172a; font-size: 14px;">${poiTitle}</b>
          <p style="color: #64748b; font-size: 12px; margin: 4px 0;">${p.address || 'Quận 4'}</p>
        </div>
      `);
      marker.on('click', () => {
        setActivePoi(p);
      });

      poiMarkersRef.current.push(marker);
    });
  }, [pois, activePoi, lang]);

  // 6. Proximity Geofencing & Auto Audio Playback
  useEffect(() => {
    if ((!hasRealGps && !isSimulatingGps) || !autoPlayEnabled || pois.length === 0) return;

    for (const p of pois) {
      const coords = p.location?.coordinates;
      if (!coords) continue;
      const [lon, lat] = coords;
      const dist = calculateDistanceMeters(currentLat, currentLng, lat, lon);
      const radius = p.trigger_radius || 35;
      const pId = p.id || p._id;

      if (dist <= radius && !playedPoiIds.has(pId)) {
        // Trigger narration audio!
        setActivePoi(p);
        setPlayedPoiIds((prev) => new Set(prev).add(pId));
        playAudio(p);
        break;
      }
    }
  }, [currentLat, currentLng, hasRealGps, isSimulatingGps, autoPlayEnabled, pois, playedPoiIds]);

  const playAudio = (poi: any, targetLang?: LangCode) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    const currentCode = targetLang || lang;
    const poiId = poi.id || poi._id;

    // Resolve audio URL corresponding strictly to the chosen language
    const rawUrl = 
      poi.translations?.[currentCode]?.audio_url ||
      poi.published_contents?.[currentCode]?.audio_url ||
      `/storage/audio/${poiId}_${currentCode}.mp3`;

    // Add cache-busting timestamp so Cloudflare CDN serves the latest TTS audio
    const soundUrl = rawUrl.includes('?') ? `${rawUrl}&t=${Date.now()}` : `${rawUrl}?t=${Date.now()}`;

    console.log(`[TourVoice] Playing audio for POI "${poiId}" in [${currentCode}]: ${soundUrl}`);
    const audio = new Audio(soundUrl);
    audioRef.current = audio;
    audio.play().then(() => {
      setIsPlaying(true);
      // Track telemetry start
      fetch(apiUrl('/analytics/events/batch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          events: [{
            event_id: 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8),
            event_type: 'audio_play',
            poi_id: poiId,
            locale: currentCode,
            device_id: 'web_' + (user?.id || 'tourist'),
            properties: { sound_url: soundUrl }
          }]
        })
      }).catch(() => {});
    }).catch((err) => {
      console.warn('Audio play error:', err);
      setIsPlaying(false);
    });

    audio.onended = () => {
      setIsPlaying(false);
      // Track telemetry completion
      fetch(apiUrl('/analytics/events/batch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          events: [{
            event_id: 'ev_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8),
            event_type: 'audio_completed',
            poi_id: poiId,
            locale: currentCode,
            device_id: 'web_' + (user?.id || 'tourist')
          }]
        })
      }).catch(() => {});
    };
  };

  const handleLanguageChange = (newLang: LangCode) => {
    setLang(newLang);
    fetchPOIs(newLang);
    if (activePoi) {
      const updated = pois.find((p: any) => (p.id || p._id) === (activePoi.id || activePoi._id));
      const target = updated || activePoi;
      setActivePoi(target);
      if (isPlaying) {
        playAudio(target, newLang);
      }
    }
  };

  const togglePlay = () => {
    if (!activePoi) return;
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      playAudio(activePoi, lang);
    }
  };

  const handleLocateMe = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([currentLat, currentLng], 17);
    }
  };

  // Auth Gate Actions
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(apiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: authEmail.trim(), password: authPassword })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Đăng nhập thất bại. Kiểm tra email/mật khẩu.');
      }
      login(data.access_token, data.user);
      setShowAuthGate(false);
    } catch (err: any) {
      setAuthError(err.message || 'Đăng nhập thất bại.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(apiUrl('/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: authFullName,
          email: authEmail.trim(),
          password: authPassword,
          role: 'tourist'
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Đăng ký tài khoản thất bại');
      
      // Auto login after register
      const loginRes = await fetch(apiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: authEmail.trim(), password: authPassword })
      });
      const loginData = await loginRes.json();
      if (loginRes.ok && loginData.access_token) {
        login(loginData.access_token, loginData.user);
      }
      setShowAuthGate(false);
    } catch (err: any) {
      setAuthError(err.message || 'Đăng ký tài khoản thất bại.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleGuestAccess = async () => {
    setAuthLoading(true);
    try {
      const res = await fetch(apiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: 'tourist@test.vn', password: 'User@123456' })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        login(data.access_token, data.user);
      }
      setShowAuthGate(false);
    } catch {
      setShowAuthGate(false);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    if (googleLoading) return;
    setGoogleLoading(true);
    setAuthError(null);
    try {
      const res = await fetch(apiUrl('/auth/google/start?return_to=/client'), {
        method: 'GET',
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.error || 'Google OAuth chưa sẵn sàng trên máy chủ.');
      }
      window.location.href = data.auth_url;
    } catch (err: any) {
      setAuthError(err.message || 'Lỗi kết nối với Google.');
      setGoogleLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white font-['Plus_Jakarta_Sans',sans-serif] overflow-hidden">
      {/* Top Navbar */}
      <header className="h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between shrink-0 z-30">
        <div className="flex items-center space-x-3">
          <img
            src="/logo-ngang.png"
            alt="TourVoice Quận 4"
            className="h-8 sm:h-9 w-auto object-contain shrink-0"
          />
          <span className="hidden md:inline-flex text-[10px] uppercase font-bold bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/25">
            Realtime GPS
          </span>
        </div>

        {/* Controls: GPS status, Locate button, Language switcher, Auth status */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* GPS Live Badge */}
          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-xs">
            <span className={`w-2.5 h-2.5 rounded-full ${hasRealGps ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'}`} />
            <span className="font-mono text-slate-300">
              {hasRealGps ? `GPS: ±${accuracy}m` : t.gpsWaiting}
            </span>
          </div>

          <button
            onClick={handleLocateMe}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-400 hover:text-white transition-colors border border-slate-700 shadow"
            title={t.locateMe}
          >
            <Navigation className="w-4 h-4" />
          </button>

          {/* Mobile POI List Button */}
          <button
            onClick={() => setShowMobilePoiList(true)}
            className="md:hidden flex items-center space-x-1 px-2.5 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700 text-xs font-semibold transition-all shrink-0"
            title="Xem danh sách 21 điểm đến"
          >
            <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>{pois.length} Điểm</span>
          </button>

          {/* Tours Selector Button */}
          <button
            onClick={() => setShowToursModal(true)}
            className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all shadow-md active:scale-95 border ${
              activeTour
                ? 'bg-indigo-600 text-white border-indigo-500 shadow-indigo-600/30'
                : 'bg-slate-800 text-slate-200 hover:bg-slate-700 border-slate-700'
            }`}
            title="Xem và chọn tuyến tour du lịch Quận 4"
          >
            <Route className="w-4 h-4 text-indigo-400" />
            <span className="hidden sm:inline">
              {activeTour ? 'Đang Đi Tour' : `Tuyến Tour (${tours.length})`}
            </span>
          </button>

          {/* Directions / Routing Button */}
          <button
            onClick={() => setShowRouteModal(true)}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md text-xs font-semibold active:scale-95"
            title="Tìm đường đi giữa các địa điểm hoặc từ vị trí của bạn"
          >
            <Route className="w-4 h-4" />
            <span className="hidden sm:inline">Tìm Đường</span>
          </button>

          {/* GPS Simulation Toggle */}
          <button
            onClick={() => setIsSimulatingGps(!isSimulatingGps)}
            className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
              isSimulatingGps
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-lg shadow-amber-500/20 animate-pulse'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
            title="Bật/Tắt chế độ mô phỏng GPS (click bản đồ để di chuyển)"
          >
            <Compass className="w-4 h-4" />
            <span className="hidden md:inline">{isSimulatingGps ? 'Mô Phỏng: BẬT' : 'Mô Phỏng GPS'}</span>
          </button>

          {/* Multi-language Dropdown */}
          <div className="relative flex items-center bg-slate-800 border border-slate-700 rounded-xl px-2 py-1">
            <Globe className="w-4 h-4 text-indigo-400 mr-1.5 shrink-0" />
            <select
              value={lang}
              onChange={(e) => handleLanguageChange(e.target.value as LangCode)}
              className="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer pr-1"
            >
              {(Object.keys(I18N) as LangCode[]).map((code) => (
                <option key={code} value={code} className="bg-slate-900 text-white">
                  {I18N[code].flag} {I18N[code].name}
                </option>
              ))}
            </select>
          </div>

          {/* User Status / Login */}
          {user ? (
            <div className="flex items-center space-x-2 pl-2">
              <span className="text-xs font-semibold text-slate-300 hidden md:inline">{user.full_name || user.email}</span>
              <span className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-xs font-bold text-indigo-300">
                {user.full_name ? user.full_name[0].toUpperCase() : 'U'}
              </span>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthGate(true)}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-md"
            >
              {t.loginBtn}
            </button>
          )}
        </div>
      </header>

      {/* Main Area: Fullscreen Map + Floating Nearby POI List */}
      <div className="flex-1 relative overflow-hidden">
        {/* Real Interactive Leaflet Map */}
        <div ref={mapContainerRef} className="w-full h-full z-0" />

        {/* GPS Simulation Notice Banner */}
        {isSimulatingGps && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-amber-500/95 backdrop-blur-md text-slate-950 font-bold text-xs px-4 py-2 rounded-2xl shadow-2xl flex items-center space-x-2 border border-amber-400 animate-bounce">
            <Compass className="w-4 h-4" />
            <span>Chế độ mô phỏng GPS: Nhấp chuột vị trí bất kỳ trên bản đồ để di chuyển du khách!</span>
          </div>
        )}

        {/* Active Tour Floating Header Banner */}
        {activeTour && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-slate-900/95 backdrop-blur-md border border-indigo-500/60 rounded-2xl px-4 py-2.5 shadow-2xl flex items-center space-x-3 text-xs">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-ping" />
              <span className="text-slate-400 font-medium">Đang khám phá:</span>
              <span className="font-bold text-white max-w-[200px] truncate">{activeTour.name}</span>
              <span className="bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-md font-bold">
                {activeTour.pois?.length || 0} điểm dừng
              </span>
            </div>
            <button
              onClick={clearActiveTour}
              className="p-1 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
              title="Dừng tuyến tour này"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Floating Side Panel: POIs List */}
        <div className="absolute top-4 left-4 z-20 w-80 max-h-[calc(100vh-140px)] bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-3xl p-4 shadow-2xl flex flex-col hidden md:flex">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-sm font-bold text-white tracking-tight flex items-center space-x-2">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
              <span>{t.poisNearby}</span>
            </h2>
            <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-400 font-mono">
              {pois.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 mt-3 pr-1">
            {pois.map((p) => {
              const coords = p.location?.coordinates || [106.7042, 10.7635];
              const dist = calculateDistanceMeters(currentLat, currentLng, coords[1], coords[0]);
              const isSelected = activePoi?.id === p.id;
              const nameText = getPoiName(p);
              const descText = getPoiDesc(p);

              return (
                <div
                  key={p.id || p._id}
                  onClick={() => {
                    setActivePoi(p);
                    if (mapInstanceRef.current) {
                      mapInstanceRef.current.setView([coords[1], coords[0]], 17);
                    }
                  }}
                  className={`p-3 rounded-2xl cursor-pointer transition-all border ${
                    isSelected
                      ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-lg'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <h3 className="text-xs font-bold truncate flex-1">{nameText}</h3>
                    <span className="text-[11px] font-mono text-emerald-400 shrink-0 font-semibold">
                      {dist}m
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{descText || p.address || 'Quận 4'}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Audio Player Bar - Minimized Compact Pill */}
        {activePoi && playerMinimized && (
          <div className="absolute bottom-4 left-4 right-4 md:left-96 md:right-8 z-20 bg-slate-900/95 backdrop-blur-md border border-indigo-500/40 rounded-2xl p-2.5 shadow-2xl flex items-center justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-center space-x-2.5 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                <Headphones className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-bold text-white truncate">{getPoiName(activePoi)}</span>
                  <span className="text-[11px] shrink-0">{I18N[lang].flag}</span>
                </div>
                <p className="text-[10px] text-emerald-400 font-mono">
                  {calculateDistanceMeters(currentLat, currentLng, activePoi.location?.coordinates?.[1] || 10.7635, activePoi.location?.coordinates?.[0] || 106.7042)}m
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-1.5 shrink-0">
              <button
                onClick={togglePlay}
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-md"
                title={isPlaying ? 'Tạm dừng' : 'Nghe thuyết minh'}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>

              <button
                onClick={() => setPlayerMinimized(false)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700"
                title="Mở rộng thanh phát"
              >
                <ChevronUp className="w-4 h-4" />
              </button>

              <button
                onClick={() => {
                  setActivePoi(null);
                  if (audioRef.current) audioRef.current.pause();
                  setIsPlaying(false);
                }}
                className="p-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                title="Đóng trình phát"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Bottom Audio Player Bar - Expanded Full Controls */}
        {activePoi && !playerMinimized && (
          <div className="absolute bottom-4 left-4 right-4 md:left-96 md:right-8 z-20 bg-slate-900/95 backdrop-blur-lg border border-slate-800 rounded-3xl p-4 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4 animate-in fade-in duration-200">
            {/* Top-right quick collapse & close buttons */}
            <div className="absolute top-3 right-3 flex items-center space-x-1 z-10">
              <button
                onClick={() => setPlayerMinimized(true)}
                className="p-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                title="Thu nhỏ thanh phát"
              >
                <ChevronDown className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setActivePoi(null);
                  if (audioRef.current) audioRef.current.pause();
                  setIsPlaying(false);
                }}
                className="p-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                title="Đóng trình phát"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center space-x-3 min-w-0 flex-1 pr-16 sm:pr-0">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
                <Headphones className="w-6 h-6" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {t[activePoi.category as keyof typeof t] || activePoi.category}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-mono flex items-center space-x-1">
                    <span>{I18N[lang].flag}</span>
                    <span>{I18N[lang].name}</span>
                  </span>
                  <span className="text-xs text-emerald-400 font-mono">
                    {t.distanceLabel}: {calculateDistanceMeters(currentLat, currentLng, activePoi.location?.coordinates?.[1] || 10.7635, activePoi.location?.coordinates?.[0] || 106.7042)}m
                  </span>
                </div>
                <h3 className="text-sm font-bold text-white truncate mt-0.5">{getPoiName(activePoi)}</h3>
                <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{getPoiDesc(activePoi)}</p>
              </div>
            </div>

            {/* Player Controls */}
            <div className="flex items-center space-x-2 sm:space-x-3 shrink-0 flex-wrap justify-center sm:justify-end gap-y-2">
              <button
                onClick={() => setAutoPlayEnabled(!autoPlayEnabled)}
                className={`text-xs px-3 py-1.5 rounded-xl border transition-all ${
                  autoPlayEnabled
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                {autoPlayEnabled ? t.autoAudioOn : t.autoAudioOff}
              </button>

              <button
                onClick={() => routeToPoi(activePoi)}
                disabled={routeLoading}
                className="inline-flex items-center space-x-1.5 px-3.5 sm:px-4 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-2xl text-xs font-semibold shadow-lg shadow-sky-600/30 transition-all active:scale-95"
                title="Chỉ đường từ vị trí của bạn đến địa điểm này"
              >
                <Navigation2 className="w-4 h-4" />
                <span>Chỉ Đường</span>
              </button>

              {isSimulatingGps && (
                <button
                  onClick={() => simulateMoveToPoi(activePoi)}
                  className="inline-flex items-center space-x-1.5 px-3 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 rounded-2xl text-xs font-semibold transition-all active:scale-95"
                  title="Di chuyển du khách đến điểm này trong chế độ mô phỏng"
                >
                  <Compass className="w-3.5 h-3.5" />
                  <span>Tới Điểm Này</span>
                </button>
              )}

              <button
                onClick={togglePlay}
                className="inline-flex items-center space-x-2 px-4 sm:px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span>{isPlaying ? 'Tạm Dừng' : t.listenNarration}</span>
              </button>
            </div>
          </div>
        )}

        {/* Mobile POI Drawer / Bottom Sheet */}
        {showMobilePoiList && (
          <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/80 backdrop-blur-sm md:hidden animate-in fade-in duration-200">
            <div
              className="fixed inset-0"
              onClick={() => setShowMobilePoiList(false)}
            />
            <div className="relative bg-[#0E131F] border-t border-slate-800 rounded-t-3xl max-h-[80vh] flex flex-col shadow-2xl z-10">
              {/* Handlebar */}
              <div className="w-12 h-1.5 bg-slate-700 rounded-full mx-auto my-3 shrink-0" />

              {/* Header */}
              <div className="px-5 pb-3 border-b border-slate-800/80 flex items-center justify-between shrink-0">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                    <Radio className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">Điểm Thuyết Minh Quận 4</h3>
                    <p className="text-[11px] text-slate-400">{pois.length} địa điểm theo khoảng cách</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowMobilePoiList(false)}
                  className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Search */}
              <div className="p-3 border-b border-slate-800/60 shrink-0">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={mobilePoiSearch}
                    onChange={(e) => setMobilePoiSearch(e.target.value)}
                    placeholder="Tìm nhanh di tích, quán ăn..."
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* POI Scroll List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                {pois
                  .filter((p) => {
                    if (!mobilePoiSearch.trim()) return true;
                    const q = mobilePoiSearch.toLowerCase();
                    const name = getPoiName(p).toLowerCase();
                    const desc = (getPoiDesc(p) || '').toLowerCase();
                    return name.includes(q) || desc.includes(q);
                  })
                  .map((p) => {
                    const coords = p.location?.coordinates || [106.7042, 10.7635];
                    const dist = calculateDistanceMeters(currentLat, currentLng, coords[1], coords[0]);
                    const isSelected = activePoi?.id === p.id;
                    const nameText = getPoiName(p);
                    const descText = getPoiDesc(p);

                    return (
                      <div
                        key={p.id || p._id}
                        onClick={() => {
                          setActivePoi(p);
                          setPlayerMinimized(false);
                          setShowMobilePoiList(false);
                          if (mapInstanceRef.current) {
                            mapInstanceRef.current.setView([coords[1], coords[0]], 17);
                          }
                        }}
                        className={`p-3 rounded-2xl cursor-pointer transition-all border ${
                          isSelected
                            ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-lg'
                            : 'bg-slate-900/90 border-slate-800/90 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-1">
                          <h4 className="text-xs font-bold text-white truncate flex-1">{nameText}</h4>
                          <span className="text-[11px] font-mono text-emerald-400 shrink-0 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                            {dist}m
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{descText || p.address || 'Quận 4'}</p>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        )}

        {/* Active Route Floating Card */}
        {currentRoute && (
          <div className="absolute top-4 right-4 z-20 max-w-sm w-full bg-slate-900/95 backdrop-blur-md border border-sky-500/40 rounded-3xl p-4 shadow-2xl flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-sky-500/20 text-sky-400 flex items-center justify-center border border-sky-500/30">
                  {routeMode === 'walking' && <Footprints className="w-4 h-4" />}
                  {routeMode === 'driving' && <Car className="w-4 h-4" />}
                  {routeMode === 'cycling' && <Bike className="w-4 h-4" />}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Lộ Trình Đang Chỉ Dẫn</h4>
                  <div className="flex items-center space-x-2 mt-0.5 text-xs">
                    <span className="font-extrabold text-sky-400 text-sm">{currentRoute.distance_display}</span>
                    <span className="text-slate-400">•</span>
                    <span className="font-semibold text-emerald-400">{currentRoute.duration_display}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={clearRoute}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-all"
                title="Tắt lộ trình"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-300">
              <button
                onClick={() => setShowTurnByTurn(!showTurnByTurn)}
                className="text-sky-400 hover:text-sky-300 font-medium underline flex items-center gap-1"
              >
                <CornerDownRight className="w-3.5 h-3.5" />
                <span>{showTurnByTurn ? 'Ẩn chi tiết ngã rẽ' : 'Xem chi tiết các ngã rẽ'}</span>
              </button>
              <button
                onClick={clearRoute}
                className="text-rose-400 hover:text-rose-300 font-medium text-[11px]"
              >
                Hủy chỉ đường
              </button>
            </div>

            {/* Turn by turn expandable list */}
            {showTurnByTurn && currentRoute.steps && (
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1 text-xs divide-y divide-slate-800/60 border-t border-slate-800 pt-2">
                {currentRoute.steps.map((s: any, idx: number) => (
                  <div key={idx} className="pt-1.5 flex items-start gap-2 text-slate-300">
                    <span className="font-mono text-sky-400 text-[10px] w-4 mt-0.5 shrink-0">{idx + 1}.</span>
                    <div className="flex-1">
                      <p className="font-medium text-white">{s.instruction}</p>
                      <p className="text-[10px] text-slate-400">{s.distance_display} • {s.duration_display}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Route Planning Modal */}
        {showRouteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-md shadow-2xl space-y-5">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
                    <Route className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Tìm Đường Du Lịch Quận 4</h3>
                    <p className="text-xs text-slate-400">Chỉ dẫn lộ trình chính xác theo đường phố OSRM</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowRouteModal(false)}
                  className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Origin Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">1. Điểm Xuất Phát:</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRouteOriginType('my_location')}
                    className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                      routeOriginType === 'my_location'
                        ? 'bg-sky-600/20 border-sky-500 text-sky-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    <span>Vị Trí Của Tôi</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRouteOriginType('poi')}
                    className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center justify-center gap-1.5 ${
                      routeOriginType === 'poi'
                        ? 'bg-sky-600/20 border-sky-500 text-sky-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Chọn Địa Điểm (A)</span>
                  </button>
                </div>

                {routeOriginType === 'poi' && (
                  <select
                    value={routeOriginPoiId}
                    onChange={(e) => setRouteOriginPoiId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">-- Chọn điểm xuất phát (POI A) --</option>
                    {pois.map((p) => (
                      <option key={p.id || p._id} value={p.id || p._id}>
                        {getPoiName(p)}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Destination Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">2. Điểm Đến (POI B):</label>
                <select
                  value={routeDestPoiId}
                  onChange={(e) => setRouteDestPoiId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Chọn điểm đến (POI B) --</option>
                  {pois.map((p) => (
                    <option key={p.id || p._id} value={p.id || p._id}>
                      {getPoiName(p)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Travel Mode */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">3. Phương Tiện Di Chuyển:</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setRouteMode('walking')}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold border flex flex-col items-center gap-1 transition-all ${
                      routeMode === 'walking'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400'
                    }`}
                  >
                    <Footprints className="w-4 h-4" />
                    <span>Đi Bộ</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRouteMode('driving')}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold border flex flex-col items-center gap-1 transition-all ${
                      routeMode === 'driving'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400'
                    }`}
                  >
                    <Car className="w-4 h-4" />
                    <span>Xe Máy / Ô tô</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setRouteMode('cycling')}
                    className={`py-2 px-2 rounded-xl text-xs font-semibold border flex flex-col items-center gap-1 transition-all ${
                      routeMode === 'cycling'
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400'
                    }`}
                  >
                    <Bike className="w-4 h-4" />
                    <span>Xe Đạp</span>
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="button"
                  disabled={routeLoading || !routeDestPoiId}
                  onClick={() => calculateRoute(routeOriginType, routeOriginPoiId, routeDestPoiId, routeMode)}
                  className="w-full py-3 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-bold shadow-lg shadow-sky-600/30 transition-all flex items-center justify-center gap-2"
                >
                  {routeLoading ? (
                    <span>Đang tính toán tuyến đường...</span>
                  ) : (
                    <>
                      <Navigation2 className="w-4 h-4" />
                      <span>Xem Lộ Trình Trên Bản Đồ</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Auth Gate Modal Overlay */}
      {showAuthGate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 w-full max-w-md shadow-2xl text-center space-y-6">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-400">
              <Lock className="w-8 h-8" />
            </div>

            <div>
              <h2 className="text-xl font-black text-white">{t.authRequiredTitle}</h2>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">{t.authRequiredDesc}</p>
            </div>

            {/* Google Login for Tourists */}
            <div>
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={googleLoading || authLoading}
                className="w-full py-3 px-4 bg-white hover:bg-slate-100 text-slate-900 rounded-xl font-bold shadow-lg flex items-center justify-center space-x-2.5 transition-all text-xs active:scale-[0.99]"
              >
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>{googleLoading ? 'Đang kết nối Google...' : 'Đăng nhập nhanh bằng Google'}</span>
              </button>

              <div className="relative my-3">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800"></div>
                </div>
                <div className="relative flex justify-center text-[10px] uppercase">
                  <span className="bg-slate-900 px-2 text-slate-500 font-semibold tracking-wider">
                    Hoặc bằng tài khoản email / khách
                  </span>
                </div>
              </div>
            </div>

            {/* Tabs: Login vs Register */}
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                type="button"
                onClick={() => setAuthTab('login')}
                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                  authTab === 'login' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.loginTab}
              </button>
              <button
                type="button"
                onClick={() => setAuthTab('register')}
                className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
                  authTab === 'register' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                }`}
              >
                {t.registerTab}
              </button>
            </div>

            {authError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs font-medium">
                {authError}
              </div>
            )}

            {/* Auth Form */}
            <form onSubmit={authTab === 'login' ? handleLoginSubmit : handleRegisterSubmit} className="space-y-3 text-left">
              {authTab === 'register' && (
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">{t.nameLabel}</label>
                  <input
                    type="text"
                    required
                    value={authFullName}
                    onChange={(e) => setAuthFullName(e.target.value)}
                    placeholder="Nguyễn Văn A"
                    className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">{t.emailLabel}</label>
                <input
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="tourist@test.vn"
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">{t.passLabel}</label>
                <input
                  type="password"
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 mt-2"
              >
                {authLoading ? 'Đang xác thực...' : (authTab === 'login' ? t.loginBtn : t.registerBtn)}
              </button>
            </form>

            <div className="pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={handleGuestAccess}
                disabled={authLoading}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition-colors flex items-center justify-center space-x-1.5"
              >
                <span>{t.guestBtn}</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tours Selection Modal */}
      {showToursModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-2xl shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                  <Route className="w-5 h-5 text-indigo-400" />
                  <span>Khám Phá Tuyến Du Lịch Quận 4</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Lựa chọn lộ trình có sẵn với các điểm dừng tối ưu và thuyết minh tự động
                </p>
              </div>
              <button
                onClick={() => setShowToursModal(false)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 space-y-3 pr-1">
              {tourLoading ? (
                <div className="text-center py-12 text-slate-400">Đang tải thông tin lộ trình tour...</div>
              ) : tours.length === 0 ? (
                <div className="text-center py-12 text-slate-500">Chưa có tuyến tour nào được công bố.</div>
              ) : (
                tours.map((t: any) => {
                  const tourId = t.id || t._id;
                  const isCurrentActive = activeTour?.id === tourId || (activeTour as any)?._id === tourId;
                  const isTourPaid = t.is_paid || (t.price_amount && t.price_amount > 0);

                  return (
                    <div
                      key={tourId}
                      className={`p-4 rounded-2xl border transition-all ${
                        isCurrentActive
                          ? 'bg-indigo-600/15 border-indigo-500'
                          : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold text-indigo-400 flex items-center space-x-1.5">
                          <Route className="w-3.5 h-3.5" />
                          <span>{t.poi_count || t.poi_ids?.length || 0} điểm dừng</span>
                        </span>
                        {isTourPaid ? (
                          <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-bold border border-amber-500/20">
                            {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(t.price_vnd || t.price_amount || 0)}
                          </span>
                        ) : (
                          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">
                            Miễn Phí
                          </span>
                        )}
                      </div>

                      <h4 className="font-bold text-white text-base">{t.name || t.title}</h4>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{t.description || 'Chưa có mô tả'}</p>

                      <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-800/80">
                        <span className="text-[11px] text-slate-500">
                          {isCurrentActive ? '🟢 Tuyến đang kích hoạt trên bản đồ' : 'Lộ trình tham quan từng bước'}
                        </span>
                        <button
                          onClick={() => selectTour(tourId)}
                          disabled={tourLoading}
                          className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                            isCurrentActive
                              ? 'bg-emerald-600 text-white'
                              : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
                          }`}
                        >
                          {isCurrentActive ? 'Đang Khám Phá' : 'Bắt Đầu Khám Phá'}
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
