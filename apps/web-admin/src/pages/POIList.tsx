import React, { useEffect, useState, useRef } from 'react';
import LocalizationJobs from '../components/LocalizationJobs';
import { DEFAULT_TILE_URL, DEFAULT_ATTRIBUTION, configureMapTiles } from '../services/mapTiles';
import { 
  Plus, 
  Search, 
  MapPin, 
  Headphones, 
  CheckCircle, 
  AlertCircle, 
  Trash2,
  Edit3,
  Crosshair,
  Mic,
  Square,
  Upload,
  Globe,
  ChevronLeft,
  ChevronRight,
  Clock,
  Sparkles,
  Play,
  Pause,
  Volume2,
  RefreshCw,
  X,
  Wand2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { poiService, POI } from '../services/poiService';
import { apiUrl } from '../config/runtime';
import { Badge, Button, Card, PageHeader, EmptyState, Modal } from '../components/ui';

interface MapPickerProps {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number) => void;
}

const MapPicker: React.FC<MapPickerProps> = ({ lat, lng, onChange }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const L = (window as any).L;
    if (!L) return;

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const safeLat = isNaN(lat) ? 10.7635 : lat;
    const safeLng = isNaN(lng) ? 106.7042 : lng;

    const map = L.map(containerRef.current).setView([safeLat, safeLng], 15);
    const tiles = L.tileLayer(DEFAULT_TILE_URL, {
      attribution: DEFAULT_ATTRIBUTION,
      maxZoom: 20
    }).addTo(map);
    void configureMapTiles(tiles);

    const marker = L.marker([safeLat, safeLng], { draggable: true }).addTo(map);
    marker.on('dragend', (e: any) => {
      const p = e.target.getLatLng();
      onChange(parseFloat(p.lat.toFixed(6)), parseFloat(p.lng.toFixed(6)));
    });

    map.on('click', (e: any) => {
      marker.setLatLng(e.latlng);
      onChange(parseFloat(e.latlng.lat.toFixed(6)), parseFloat(e.latlng.lng.toFixed(6)));
    });

    mapRef.current = map;
    markerRef.current = marker;

    const timer = setTimeout(() => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
      }
    }, 250);

    return () => {
      clearTimeout(timer);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (mapRef.current && markerRef.current) {
      const safeLat = isNaN(lat) ? 10.7635 : lat;
      const safeLng = isNaN(lng) ? 106.7042 : lng;
      const currentPos = markerRef.current.getLatLng();
      if (Math.abs(currentPos.lat - safeLat) > 0.00001 || Math.abs(currentPos.lng - safeLng) > 0.00001) {
        markerRef.current.setLatLng([safeLat, safeLng]);
        mapRef.current.setView([safeLat, safeLng]);
        mapRef.current.invalidateSize();
      }
    }
  }, [lat, lng]);

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-700 shadow-inner">
      <div ref={containerRef} className="w-full h-56 z-0" />
      <div className="absolute bottom-2 left-2 bg-slate-900/90 backdrop-blur-md px-2.5 py-1 rounded-md text-[11px] font-mono text-slate-300 border border-slate-700 pointer-events-none z-[1000]">
        📍 Click hoặc kéo ghim để chọn chính xác tọa độ
      </div>
    </div>
  );
};

export const POIList: React.FC = () => {
  const { user, token } = useAuth();
  const [pois, setPois] = useState<POI[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [queuedTasks, setQueuedTasks] = useState<string[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiRefining, setAiRefining] = useState(false);
  const [aiNarrating, setAiNarrating] = useState(false);
  const [aiTranslatingMulti, setAiTranslatingMulti] = useState(false);
  const [aiTone, setAiTone] = useState<'cuốn hút' | 'lịch sử' | 'hài hước' | 'ngắn gọn'>('cuốn hút');

  // Pagination State
  const [page, setPage] = useState(1);
  const pageSize = 9;

  // Modal State (Create or Edit)
  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editPoiId, setEditPoiId] = useState<string | null>(null);

  // Delete Confirmation Modal State
  const [deleteConfirmPoi, setDeleteConfirmPoi] = useState<POI | null>(null);

  // Form Fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [address, setAddress] = useState('');
  const [cat, setCat] = useState('sightseeing');
  const [lng, setLng] = useState('106.7042');
  const [lat, setLat] = useState('10.7635');
  const [radius, setRadius] = useState('30.0');
  const [priority, setPriority] = useState('1');
  const [audioUrl, setAudioUrl] = useState('');
  const [audioDurationMs, setAudioDurationMs] = useState(0);

  // Audio Recording State
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Multilingual Detail & Audio Preview Modal State
  const [multilingualModalOpen, setMultilingualModalOpen] = useState(false);
  const [selectedPoiForMulti, setSelectedPoiForMulti] = useState<any | null>(null);
  const [activeLangTab, setActiveLangTab] = useState<'vi' | 'en' | 'fr' | 'ja' | 'ko' | 'zh'>('vi');
  const [isPlayingMultiAudio, setIsPlayingMultiAudio] = useState(false);
  const multiAudioRef = useRef<HTMLAudioElement | null>(null);
  const [recreatingLang, setRecreatingLang] = useState<string | null>(null);
  const [ttsTargetLang, setTtsTargetLang] = useState<string>('vi');

  useEffect(() => {
    return () => {
      if (multiAudioRef.current) {
        multiAudioRef.current.pause();
      }
    };
  }, []);

  const handleAiAutoFill = async () => {
    if (!name.trim()) {
      alert('Vui lòng nhập tên quán hoặc địa điểm trước khi nhờ AI nhận diện.');
      return;
    }

    setAiLoading(true);
    try {
      const data = await poiService.poiAssistant({
        poi_name: name.trim(),
        address_hint: address.trim() || undefined,
        category_hint: cat || undefined
      });

      if (data) {
        if (data.name && data.name !== name) {
          setName(data.name);
        }
        if (data.description) {
          setDescription(data.description);
        }
        if (data.address) {
          setAddress(data.address);
        }
        if (data.category) {
          setCat(data.category);
        }
        if (data.latitude && data.longitude) {
          setLat(String(data.latitude));
          setLng(String(data.longitude));
        }

        setMessage({
          type: 'success',
          text: `✨ AI đã nhận diện thành công: "${data.name}"! Các trường mô tả, địa chỉ và phân loại đã được điền tự động. Bạn có thể kiểm tra và chỉnh sửa trước khi lưu.`
        });
      }
    } catch (e: any) {
      console.error('AI autofill error:', e);
      alert('Không thể kết nối dịch vụ Gemini AI: ' + (e.message || 'Lỗi hệ thống'));
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiRefineDescription = async () => {
    if (!name.trim()) {
      alert('Vui lòng nhập tên địa điểm trước khi nhờ Gemini AI tối ưu mô tả.');
      return;
    }
    setAiRefining(true);
    try {
      const res = await poiService.refineDescription({
        poi_name: name.trim(),
        current_description: description.trim() || undefined,
        category: cat,
        address: address.trim() || undefined,
        tone: aiTone,
      });
      if (res && res.refined_description) {
        setDescription(res.refined_description);
        setMessage({
          type: 'success',
          text: `✨ Gemini AI đã tối ưu mô tả cho "${res.poi_name}" (${aiTone})! Đoạn văn đã được làm mới sinh động và hấp dẫn hơn.`,
        });
      }
    } catch (e: any) {
      console.error('Gemini refine error:', e);
      alert('Không thể kết nối Gemini AI để tối ưu mô tả: ' + (e.message || 'Lỗi hệ thống'));
    } finally {
      setAiRefining(false);
    }
  };

  const handleAiGenerateNarration = async () => {
    if (!name.trim()) {
      alert('Vui lòng nhập tên địa điểm trước khi nhờ Gemini AI soạn thuyết minh.');
      return;
    }
    setAiNarrating(true);
    try {
      const res = await poiService.generateNarration({
        poi_name: name.trim(),
        category: cat,
        address: address.trim() || undefined,
        tone: aiTone,
        language_code: ttsTargetLang || 'vi',
      });
      if (res && res.narration_text) {
        setDescription(res.narration_text);
        setMessage({
          type: 'success',
          text: `✨ Gemini AI đã soạn xong bài thuyết minh GPS! Bạn có thể bấm "Đọc Google TTS (${(ttsTargetLang || 'VI').toUpperCase()})" để nghe giọng đọc ngay.`,
        });
      }
    } catch (e: any) {
      console.error('Gemini narration error:', e);
      alert('Không thể kết nối Gemini AI để soạn thuyết minh: ' + (e.message || 'Lỗi hệ thống'));
    } finally {
      setAiNarrating(false);
    }
  };

  const handleGeminiMultilingualTranslate = async (targetPoiId?: string) => {
    const poiIdToSync = targetPoiId || editPoiId || selectedPoiForMulti?.id || selectedPoiForMulti?._id;
    const poiNameToSync = name.trim() || selectedPoiForMulti?.name;
    const poiDescToSync = description.trim() || selectedPoiForMulti?.description;

    if (!poiNameToSync) {
      alert('Vui lòng có tên địa điểm để dịch.');
      return;
    }
    setAiTranslatingMulti(true);
    try {
      const res = await poiService.translateMultilingualGemini({
        poi_id: poiIdToSync || undefined,
        poi_name: poiNameToSync,
        description: poiDescToSync || poiNameToSync,
        category: cat || selectedPoiForMulti?.category || 'food_drink',
      });

      if (res && res.translations) {
        if (selectedPoiForMulti) {
          setSelectedPoiForMulti({
            ...selectedPoiForMulti,
            translations: {
              ...(selectedPoiForMulti.translations || {}),
              ...res.translations,
            }
          });
        }


        setMessage({
          type: 'success',
          text: 'Đã tạo bản dịch đề xuất. Kiểm tra nội dung trước khi lưu và tạo giọng đọc.',
        });
      }
    } catch (e: any) {
      console.error('Gemini multilingual error:', e);
      alert('Không thể dịch 6 ngôn ngữ qua Gemini AI: ' + (e.message || 'Lỗi hệ thống'));
    } finally {
      setAiTranslatingMulti(false);
    }
  };

  const fetchPOIs = async () => {
    setLoading(true);
    try {
      const res = await poiService.getPOIs({
        search: search.trim() || undefined,
        category: category || undefined,
        skip: 0,
        limit: 100,
      });
      setPois(res.items || []);
      setPage(1);
    } catch (err: any) {
      console.error(err);
      setMessage({ type: 'error', text: err.message || 'Không thể tải danh sách địa điểm.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPOIs();
  }, [category]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPOIs();
  };

  const openCreateModal = () => {
    setIsEditing(false);
    setEditPoiId(null);
    setName('');
    setDescription('');
    setAddress('');
    setCat('sightseeing');
    setLng('106.7042');
    setLat('10.7635');
    setRadius('30.0');
    setPriority('1');
    setAudioUrl('');
    setAudioDurationMs(0);
    setShowModal(true);
  };

  const openEditModal = (poi: any) => {
    setIsEditing(true);
    setEditPoiId(poi.id || poi._id);
    setName(poi.name || '');
    setDescription(poi.description || '');
    setAddress(poi.address || '');
    setCat(poi.category || 'sightseeing');
    const coords = poi.location?.coordinates || [106.7042, 10.7635];
    setLng(String(coords[0]));
    setLat(String(coords[1]));
    setRadius(String(poi.trigger_radius || 30.0));
    setPriority(String(poi.audio_priority || 1));
    setAudioUrl(poi.audio_url || '');
    setAudioDurationMs(poi.audio_duration_ms || 0);
    setShowModal(true);
  };

  // Real GPS Geolocation
  const handleGetRealGPS = () => {
    if (!navigator.geolocation) {
      alert('Trình duyệt không hỗ trợ định vị GPS.');
      return;
    }
    setActionLoading('gps_fetch');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const realLat = parseFloat(pos.coords.latitude.toFixed(6));
        const realLng = parseFloat(pos.coords.longitude.toFixed(6));
        setLat(String(realLat));
        setLng(String(realLng));
        setMessage({
          type: 'success',
          text: `Đã nhận GPS thật 100%: [${realLat}, ${realLng}] (Độ chính xác: ±${Math.round(pos.coords.accuracy)}m)`
        });
        setActionLoading(null);
      },
      (err) => {
        alert(`Không thể lấy GPS: ${err.message}. Vui lòng cấp quyền vị trí.`);
        setActionLoading(null);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Google TTS Voice Synthesis
  const handleGenerateGoogleTTS = async (targetLang: string = ttsTargetLang) => {
    if (!description.trim()) {
      alert('Vui lòng nhập nội dung mô tả trước khi tạo giọng đọc Google TTS.');
      return;
    }
    setActionLoading('tts_gen');
    setMessage(null);
    try {
      const textToRead = `${name ? name + '. ' : ''}${description}`;
      const data = await poiService.synthesizeGoogleTTS(textToRead, targetLang);
      setAudioUrl(data.audio_url);
      setAudioDurationMs(data.audio_duration_ms || 10000);
      const labels: Record<string, string> = {
        vi: 'tiếng Việt',
        en: 'tiếng Anh',
        fr: 'tiếng Pháp',
        ja: 'tiếng Nhật',
        ko: 'tiếng Hàn',
        zh: 'tiếng Trung'
      };
      setMessage({ type: 'success', text: `Đã tạo giọng đọc thuyết minh Google TTS ${labels[targetLang] || targetLang} thành công!` });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  // Multilingual Modal Audio Preview Handlers
  const openMultilingualModal = (poi: any, langCode: 'vi' | 'en' | 'fr' | 'ja' | 'ko' | 'zh' = 'vi') => {
    if (multiAudioRef.current) {
      multiAudioRef.current.pause();
      setIsPlayingMultiAudio(false);
    }
    setSelectedPoiForMulti(poi);
    setActiveLangTab(langCode);
    setMultilingualModalOpen(true);
  };

  const playMultilingualAudio = (url: string) => {
    if (multiAudioRef.current) {
      multiAudioRef.current.pause();
    }
    if (!url) {
      alert('Chưa có file âm thanh cho ngôn ngữ này. Hãy bấm "Tạo Lại Audio TTS".');
      return;
    }
    const playUrl = url.includes('?') ? `${url}&t=${Date.now()}` : `${url}?t=${Date.now()}`;
    const audio = new Audio(playUrl);
    multiAudioRef.current = audio;
    audio.play().then(() => {
      setIsPlayingMultiAudio(true);
    }).catch(e => {
      console.warn('Audio preview error:', e);
      setIsPlayingMultiAudio(false);
    });
    audio.onended = () => {
      setIsPlayingMultiAudio(false);
    };
  };

  const stopMultilingualAudio = () => {
    if (multiAudioRef.current) {
      multiAudioRef.current.pause();
      setIsPlayingMultiAudio(false);
    }
  };

  const handleRecreateLanguageTTS = async (poiId: string, langCode: string) => {
    setRecreatingLang(langCode);
    try {
      const langContent = selectedPoiForMulti?.translations?.[langCode] || selectedPoiForMulti?.published_contents?.[langCode];
      const textToSpeak = (langContent?.narration_text || `${langContent?.name || ''}. ${langContent?.description || ''}`).trim() || selectedPoiForMulti?.name;

      const resSynth = await poiService.synthesizeGoogleTTS(textToSpeak, langCode);
      if (resSynth.audio_url) {
        const updated = { ...selectedPoiForMulti };
        if (!updated.translations) updated.translations = {};
        if (!updated.translations[langCode]) updated.translations[langCode] = {};
        updated.translations[langCode].audio_url = resSynth.audio_url;
        setSelectedPoiForMulti(updated);
        setMessage({ type: 'success', text: `Đã tạo mới Google TTS thành công cho ${langCode.toUpperCase()}!` });
      }
    } catch (err: any) {
      alert(`Lỗi khi tạo lại TTS: ${err.message}`);
    } finally {
      setRecreatingLang(null);
    }
  };

  // Audio Recording Handlers
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mp3' });
        const localUrl = URL.createObjectURL(audioBlob);
        setAudioUrl(localUrl);
        setMessage({ type: 'success', text: 'Đã ghi âm giọng nói thành công! Bạn có thể lưu POI ngay.' });
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err: any) {
      alert(`Không thể truy cập microphone: ${err.message}`);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (editPoiId) {
      setActionLoading('upload_audio');
      try {
        const data = await poiService.uploadAudio(editPoiId, file, 'vi');
        setAudioUrl(data.audio_url);
        setAudioDurationMs(data.audio_duration_ms || 10000);
        setMessage({ type: 'success', text: 'Tải lên bản ghi âm MP3 thành công!' });
      } catch (err: any) {
        setMessage({ type: 'error', text: err.message });
      } finally {
        setActionLoading(null);
      }
    } else {
      setAudioUrl(URL.createObjectURL(file));
    }
  };

  // Submit POI Form
  const handleSubmitPOI = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('save_poi');
    setMessage(null);

    const payload = {
      name,
      description,
      category: cat,
      address,
      location: {
        type: 'Point',
        coordinates: [parseFloat(lng), parseFloat(lat)] as [number, number]
      },
      trigger_radius: parseFloat(radius),
      audio_priority: parseInt(priority, 10),
      audio_url: audioUrl || null,
      audio_duration_ms: audioDurationMs || 0,
      auto_translate: true,
      activation_requested: false
    };

    try {
      if (isEditing && editPoiId) {
        await poiService.updatePOI(editPoiId, payload);
        setMessage({
          type: 'success',
          text: `⚡ Đã lưu cập nhật POI "${name}" ngay vào database! Bản dịch 6 thứ tiếng & audio TTS đang xử lý ngầm.`
        });
      } else {
        await poiService.createPOI(payload);
        setMessage({
          type: 'success',
          text: `⚡ Đã lưu địa điểm mới "${name}" ngay vào database! Bản dịch 6 thứ tiếng & audio TTS đang xử lý ngầm.`
        });
      }
      setShowModal(false);
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  // Delete POI Handler
  const handleConfirmDelete = async () => {
    if (!deleteConfirmPoi) return;
    const targetId = deleteConfirmPoi.id || deleteConfirmPoi._id;
    if (!targetId) return;

    setActionLoading('delete_poi');
    try {
      await poiService.deletePOI(targetId);
      setMessage({
        type: 'success',
        text: `Đã xóa địa điểm "${deleteConfirmPoi.name}" và toàn bộ mã QR liên quan thành công khỏi hệ thống.`
      });
      setDeleteConfirmPoi(null);
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Xóa địa điểm thất bại.' });
    } finally {
      setActionLoading(null);
    }
  };

  // Multilingual Sync Single
  const handleSyncMultilingual = async (poiId: string) => {
    setActionLoading(`sync_${poiId}`);
    setMessage(null);
    try {
      const data = await poiService.syncMultilingual(poiId);
      setQueuedTasks([data.task_id]);
      setMessage({
        type: 'success',
        text: 'Đã đưa vào hàng đợi dịch và tạo giọng đọc. Theo dõi trạng thái bên dưới.'
      });
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  // Batch Sync All
  const handleBatchSyncAll = async () => {
    if (!window.confirm('Bạn có chắc chắn muốn đồng bộ dịch và tạo audio Google TTS 6 thứ tiếng cho toàn bộ địa điểm?')) {
      return;
    }
    setActionLoading('batch_sync');
    setMessage(null);
    try {
      const data = await poiService.batchSyncAll();
      setQueuedTasks(data.task_ids);
      setMessage({
        type: 'success',
        text: `Đã xếp lịch xử lý ${data.total_pois} địa điểm. Trạng thái thành công chỉ xuất hiện khi worker hoàn tất.`
      });
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  // Toggle Activation
  const handleToggleActive = async (poiId: string, currentActive: boolean) => {
    setActionLoading(`toggle_${poiId}`);
    setMessage(null);
    try {
      const data = await poiService.toggleActive(poiId, !currentActive);
      if (data.gate_passed === false) {
        setMessage({
          type: 'error',
          text: `Readiness Gate: ${data.message} Lý do: ${data.reasons?.join('; ') || ''}`
        });
      } else {
        setMessage({ type: 'success', text: data.message || 'Cập nhật trạng thái thành công.' });
      }
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  // Pagination Slice
  const totalPages = Math.ceil(pois.length / pageSize) || 1;
  const paginatedPOIs = pois.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Unified Page Header */}
      <PageHeader
        title="Địa Điểm Thuyết Minh"
        description="Quản lý vị trí GPS thực tế, thuyết minh Google TTS và tự động dịch 6 ngôn ngữ Quận 4"
        actions={
          <>
            {(user?.role === 'admin' || user?.role === 'super_admin') && (
              <Button
                variant="secondary"
                size="md"
                onClick={handleBatchSyncAll}
                loading={actionLoading === 'batch_sync'}
                title="Đồng bộ dịch 6 ngôn ngữ & tạo Google TTS cho toàn bộ địa điểm"
              >
                Đồng Bộ 6 Ngôn Ngữ & TTS
              </Button>
            )}

            {(user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'poi_owner') && (
              <Button
                variant="primary"
                size="md"
                onClick={openCreateModal}
              >
                + Thêm Địa Điểm Mới
              </Button>
            )}
          </>
        }
      />

      <LocalizationJobs ids={queuedTasks} onDone={() => { void fetchPOIs(); }} />
      {message && (
        <div
          className={`p-3 rounded text-xs font-medium flex items-center space-x-2 ${
            message.type === 'success'
              ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
              : 'bg-rose-950/80 border border-rose-800 text-rose-300'
          }`}
        >
          <span className={`w-2 h-2 rounded-sm ${message.type === 'success' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
          <span>{message.text}</span>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-2.5">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Tìm theo tên địa điểm hoặc địa chỉ..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-white placeholder-slate-500 text-xs focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </form>

        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-300 text-xs focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
        >
          <option value="">Tất cả danh mục</option>
          <option value="historical">Di tích lịch sử</option>
          <option value="food">Ẩm thực đêm</option>
          <option value="culture">Văn hóa tâm linh</option>
          <option value="sightseeing">Cảnh quan du lịch</option>
        </select>
      </div>

      {/* POI Cards Grid */}
      {loading ? (
        <div className="text-center py-16 text-slate-400 text-xs">Đang tải danh sách địa điểm...</div>
      ) : pois.length === 0 ? (
        <EmptyState
          title="Không tìm thấy địa điểm nào"
          description="Thử tìm kiếm với từ khóa khác hoặc thay đổi bộ lọc danh mục."
          action={
            (user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'poi_owner') ? (
              <Button variant="primary" size="sm" onClick={openCreateModal}>
                Tạo địa điểm đầu tiên
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {paginatedPOIs.map((poi: any) => {
              const poiId = poi.id || poi._id;
              const catLabels: Record<string, string> = {
                historical: 'Di tích lịch sử',
                food: 'Ẩm thực',
                culture: 'Văn hóa',
                sightseeing: 'Cảnh quan'
              };

              return (
                <Card key={poiId} className="flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2.5">
                      <Badge variant="purple" size="sm">
                        {catLabels[poi.category] || poi.category}
                      </Badge>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-[10px] text-slate-400 font-mono">r={poi.trigger_radius}m</span>
                        {poi.is_active ? (
                          <Badge variant="success" size="sm">
                            Công bố
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm">
                            Bản nháp
                          </Badge>
                        )}
                      </div>
                    </div>

                    <h3 className="text-sm font-semibold text-white line-clamp-1">{poi.name}</h3>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">{poi.description}</p>
                    
                    <div className="mt-2 text-xs text-slate-400 truncate flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{poi.address || 'Quận 4, TP.HCM'}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                      [{poi.location?.coordinates?.[1]?.toFixed(5)}, {poi.location?.coordinates?.[0]?.toFixed(5)}]
                    </p>

                    {/* Multi-language clickable buttons */}
                    <div className="flex items-center flex-wrap gap-1 mt-2.5 pt-2 border-t border-slate-800">
                      {[
                        { code: 'vi' as const, flag: '🇻🇳', label: 'VI' },
                        { code: 'en' as const, flag: '🇬🇧', label: 'EN' },
                        { code: 'fr' as const, flag: '🇫🇷', label: 'FR' },
                        { code: 'ja' as const, flag: '🇯🇵', label: 'JA' },
                        { code: 'ko' as const, flag: '🇰🇷', label: 'KO' },
                        { code: 'zh' as const, flag: '🇨🇳', label: 'ZH' },
                      ].map(({ code, flag, label }) => {
                        const hasLang = poi.translations?.[code] || poi.published_contents?.[code] || (code === 'vi' && poi.audio_url);
                        return (
                          <button
                            key={code}
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              openMultilingualModal(poi, code);
                            }}
                            className={`px-1.5 py-0.5 rounded-sm text-[10px] font-mono flex items-center space-x-1 transition-colors cursor-pointer ${
                              hasLang
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800 hover:bg-emerald-900'
                                : 'bg-slate-950 text-slate-500 border border-slate-800 hover:bg-slate-800'
                            }`}
                            title={`Xem bản dịch & audio: ${label}`}
                          >
                            <span>{flag}</span>
                            <span>{label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Audio status & Explicit Text Action Buttons */}
                  <div className="mt-4 pt-2.5 border-t border-slate-800 flex items-center justify-between gap-2">
                    <div className="flex items-center space-x-1">
                      {poi.audio_url ? (
                        <span className="text-[11px] text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded-sm border border-emerald-800 font-medium">
                          Audio {Math.round((poi.audio_duration_ms || 15000) / 1000)}s
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500">Chưa có audio</span>
                      )}
                    </div>

                    {(user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'poi_owner') ? (
                      <div className="flex items-center space-x-1">
                        {/* Multilingual Sync Button - Clear Text */}
                        <button
                          onClick={() => handleSyncMultilingual(poiId)}
                          disabled={actionLoading === `sync_${poiId}`}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 text-xs transition-colors"
                          title="Dịch tự động sang 6 thứ tiếng và tạo audio Google TTS"
                        >
                          {actionLoading === `sync_${poiId}` ? 'Đang dịch...' : 'Dịch & TTS'}
                        </button>

                        {/* Edit Button - Clear Text */}
                        <button
                          onClick={() => openEditModal(poi)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs transition-colors"
                          title="Chỉnh sửa thông tin POI & Bản đồ"
                        >
                          Sửa
                        </button>

                        {/* Delete Button - Clear Text */}
                        {(user?.role === 'admin' || user?.role === 'super_admin') && (
                          <button
                            onClick={() => setDeleteConfirmPoi(poi)}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-rose-950 text-rose-400 border border-slate-700 text-xs transition-colors"
                            title="Xóa địa điểm khỏi hệ thống"
                          >
                            Xóa
                          </button>
                        )}

                        {/* Toggle Active Button - Clear Text */}
                        <button
                          onClick={() => handleToggleActive(poiId, poi.is_active)}
                          disabled={actionLoading === `toggle_${poiId}`}
                          className={`px-2 py-1 rounded text-xs transition-colors ${
                            poi.is_active
                              ? 'bg-slate-800 hover:bg-slate-700 text-amber-300 border border-slate-700'
                              : 'bg-emerald-900 hover:bg-emerald-800 text-emerald-200 border border-emerald-700'
                          }`}
                        >
                          {poi.is_active ? 'Ẩn' : 'Công Bố'}
                        </button>
                      </div>
                    ) : (
                      <span className="text-[11px] text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        Chế độ xem
                      </span>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
              <span className="text-xs text-slate-400">
                Trang {page} / {totalPages} ({pois.length} địa điểm)
              </span>

              <div className="flex items-center space-x-1.5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs disabled:opacity-40"
                >
                  Trước
                </button>

                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
                    <button
                      key={num}
                      onClick={() => setPage(num)}
                      className={`w-6 h-6 rounded text-xs font-medium ${
                        page === num
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-900 text-slate-400 hover:bg-slate-800 border border-slate-800'
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs disabled:opacity-40"
                >
                  Sau
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmPoi && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700 rounded p-5 w-full max-w-md shadow-xl animate-in zoom-in-95 duration-150">
            <div className="flex items-center space-x-2.5 text-rose-400 mb-3">
              <div className="p-1.5 rounded bg-rose-950 border border-rose-800">
                <Trash2 className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-semibold text-white">Xác Nhận Xóa Địa Điểm</h2>
            </div>
            
            <p className="text-xs text-slate-300 mb-2">
              Bạn có chắc chắn muốn xóa địa điểm <strong className="text-white">"{deleteConfirmPoi.name}"</strong> không?
            </p>
            <p className="text-xs text-slate-400 mb-5 bg-slate-950 p-2.5 rounded border border-slate-800">
              Thao tác này sẽ xóa địa điểm, ẩn khỏi ứng dụng du khách và tự động gỡ toàn bộ các mã QR liên quan.
            </p>

            <div className="flex justify-end space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeleteConfirmPoi(null)}
              >
                Hủy bỏ
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleConfirmDelete}
                loading={actionLoading === 'delete_poi'}
              >
                Xác nhận xóa
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit POI Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700 rounded p-5 w-full max-w-2xl shadow-xl max-h-[92vh] overflow-y-auto animate-in zoom-in-95 duration-150">
            <h2 className="text-base font-semibold text-white mb-1">
              {isEditing ? `Chỉnh Sửa Địa Điểm: ${name}` : 'Thêm Địa Điểm Du Lịch Mới'}
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Chọn vị trí trên bản đồ, lấy GPS thật của máy và tạo giọng đọc Google TTS
            </p>

            <form onSubmit={handleSubmitPOI} className="space-y-3.5">
              {/* Tên POI & Nút AI Gemini */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-slate-300 uppercase">Tên Địa Điểm / Quán Ăn</label>
                  <button
                    type="button"
                    onClick={handleAiAutoFill}
                    disabled={aiLoading || !name.trim()}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors disabled:opacity-40"
                    title="Gemini AI nhận diện tên quán và tự động viết mô tả, tìm địa chỉ, chọn danh mục và tọa độ"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${aiLoading ? 'animate-spin' : ''}`} />
                    <span>{aiLoading ? 'Đang phân tích...' : 'AI Tự Điền'}</span>
                  </button>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ví dụ: Quán Ốc Oanh Vĩnh Khánh, Phá Lấu Bò Dì Nủi..."
                    className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={handleAiAutoFill}
                    disabled={aiLoading || !name.trim()}
                    className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 border border-slate-700 rounded text-xs font-medium transition-colors shrink-0 flex items-center gap-1"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Gợi Ý</span>
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Nhập tên quán rồi bấm <strong>"AI Tự Điền"</strong> để hệ thống tự điền thông tin giúp bạn.
                </p>
              </div>

              {/* Mô Tả Chi Tiết & Bộ Công Cụ Trợ Lý AI Gemini */}
              <div className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <label className="block text-xs font-medium text-slate-300 uppercase">
                      Mô Tả Chi Tiết (Nội Dung Thuyết Minh)
                    </label>
                    <span className="text-[10px] px-1.5 py-0.2 rounded-sm bg-slate-800 border border-slate-700 text-indigo-300 font-medium">
                      Gemini 3.6
                    </span>
                  </div>

                  {/* Thanh công cụ Gemini AI cho Mô tả */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    <div className="flex items-center space-x-1 bg-slate-950 border border-slate-700 rounded px-2 py-0.5">
                      <span className="text-[11px] text-slate-400">Giọng:</span>
                      <select
                        value={aiTone}
                        onChange={(e: any) => setAiTone(e.target.value)}
                        className="bg-transparent text-white text-xs focus:outline-none cursor-pointer"
                        title="Tông điệu cho bài viết của Gemini"
                      >
                        <option value="cuốn hút" className="bg-slate-900">Cuốn hút, sinh động</option>
                        <option value="lịch sử" className="bg-slate-900">Lịch sử, chiều sâu</option>
                        <option value="hài hước" className="bg-slate-900">Hài hước, vui tươi</option>
                        <option value="ngắn gọn" className="bg-slate-900">Ngắn gọn, súc tích</option>
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={handleAiRefineDescription}
                      disabled={aiRefining || !name.trim()}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-medium transition-colors disabled:opacity-40"
                    >
                      <Sparkles className={`w-3 h-3 ${aiRefining ? 'animate-spin' : ''}`} />
                      <span>{aiRefining ? 'Đang tối ưu...' : 'Tối Ưu Mô Tả'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={handleAiGenerateNarration}
                      disabled={aiNarrating || !name.trim()}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 rounded text-xs font-medium transition-colors disabled:opacity-40"
                    >
                      <Wand2 className={`w-3 h-3 ${aiNarrating ? 'animate-spin' : ''}`} />
                      <span>{aiNarrating ? 'Đang soạn...' : 'Soạn Thuyết Minh'}</span>
                    </button>
                  </div>
                </div>

                <textarea
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Nội dung lịch sử, văn hóa hoặc giới thiệu món ăn..."
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs focus:outline-none focus:border-indigo-500 transition-colors"
                />

                {/* Hàng hành động Audio & Dịch Đa Ngôn Ngữ */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-0.5">
                  <div className="flex items-center space-x-1.5">
                    <select
                      value={ttsTargetLang}
                      onChange={(e) => setTtsTargetLang(e.target.value)}
                      className="px-2 py-1 bg-slate-900 border border-slate-700 text-white rounded text-xs focus:outline-none focus:border-indigo-500"
                      title="Chọn ngôn ngữ giọng đọc TTS"
                    >
                      <option value="vi">🇻🇳 VI</option>
                      <option value="en">🇬🇧 EN</option>
                      <option value="fr">🇫🇷 FR</option>
                      <option value="ja">🇯🇵 JA</option>
                      <option value="ko">🇰🇷 KO</option>
                      <option value="zh">🇨🇳 ZH</option>
                    </select>

                    <button
                      type="button"
                      onClick={() => handleGenerateGoogleTTS(ttsTargetLang)}
                      disabled={actionLoading === 'tts_gen'}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors disabled:opacity-50"
                      title={`Tạo giọng đọc Google TTS (${ttsTargetLang.toUpperCase()})`}
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{actionLoading === 'tts_gen' ? 'Đang tạo...' : `Đọc TTS (${ttsTargetLang.toUpperCase()})`}</span>
                    </button>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      onClick={() => handleGeminiMultilingualTranslate()}
                      disabled={aiTranslatingMulti || actionLoading?.startsWith('sync_') || actionLoading === 'tts_gen'}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-medium transition-colors disabled:opacity-50"
                      title="Dịch bản địa hóa sang 6 thứ tiếng với trí tuệ nhân tạo Gemini AI và sinh giọng đọc Google TTS"
                    >
                      <Globe className={`w-3.5 h-3.5 ${aiTranslatingMulti ? 'animate-spin' : ''}`} />
                      <span>{aiTranslatingMulti ? 'Đang dịch...' : 'Dịch 6 Thứ Tiếng & TTS'}</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Audio Player / Recording Section */}
              <div className="p-3 bg-slate-950 border border-slate-700 rounded space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-300 uppercase flex items-center space-x-1.5">
                    <Headphones className="w-4 h-4 text-indigo-400" />
                    <span>File Thuyết Minh Âm Thanh</span>
                  </span>
                  
                  <div className="flex items-center space-x-2">
                    {isRecording ? (
                      <button
                        type="button"
                        onClick={stopRecording}
                        className="px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-xs font-medium flex items-center space-x-1 animate-pulse"
                      >
                        <Square className="w-3 h-3" />
                        <span>Dừng Ghi Âm</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={startRecording}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-xs font-medium flex items-center space-x-1"
                      >
                        <Mic className="w-3.5 h-3.5" />
                        <span>Ghi Âm</span>
                      </button>
                    )}

                    <label className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-xs font-medium cursor-pointer flex items-center space-x-1">
                      <Upload className="w-3.5 h-3.5" />
                      <span>Tải MP3</span>
                      <input type="file" accept="audio/*" onChange={handleFileUpload} className="hidden" />
                    </label>
                  </div>
                </div>

                {audioUrl ? (
                  <div className="flex items-center space-x-3 pt-1">
                    <audio controls src={audioUrl} className="w-full h-8" />
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500">
                    Chưa có âm thanh. Hãy bấm nút <span className="text-indigo-400 font-semibold">"Đọc TTS (VI)"</span> ở trên hoặc tải lên bản ghi âm.
                  </p>
                )}
              </div>

              {/* Danh Mục, Bán Kính & Ưu Tiên */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <div>
                  <label className="block text-xs font-medium text-slate-300 uppercase mb-1">Danh Mục</label>
                  <select
                    value={cat}
                    onChange={(e) => setCat(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs"
                  >
                    <option value="sightseeing">Cảnh quan</option>
                    <option value="historical">Di tích lịch sử</option>
                    <option value="food">Ẩm thực</option>
                    <option value="culture">Văn hóa</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 uppercase mb-1">Bán Kính GPS (mét)</label>
                  <input
                    type="number"
                    min="5"
                    max="500"
                    value={radius}
                    onChange={(e) => setRadius(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 uppercase mb-1">Độ Ưu Tiên</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs"
                  />
                </div>
              </div>

              {/* Địa Chỉ */}
              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase mb-1">Địa Chỉ</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Số 01 Nguyễn Tất Thành, Phường 12, Quận 4"
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Map Location Picker with Real GPS Button */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-medium text-slate-300 uppercase">
                    Vị Trí Bản Đồ & Tọa Độ GPS
                  </label>
                  <button
                    type="button"
                    onClick={handleGetRealGPS}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-medium transition-colors"
                  >
                    <Crosshair className="w-3.5 h-3.5" />
                    <span>Lấy GPS Thật Của Máy</span>
                  </button>
                </div>

                <MapPicker 
                  lat={parseFloat(lat) || 10.7635} 
                  lng={parseFloat(lng) || 106.7042} 
                  onChange={(newLat, newLng) => {
                    setLat(String(newLat));
                    setLng(String(newLng));
                  }} 
                />

                <div className="grid grid-cols-2 gap-2.5 pt-1">
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-0.5">Vĩ Độ (Latitude)</label>
                    <input
                      type="text"
                      required
                      value={lat}
                      onChange={(e) => setLat(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-0.5">Kinh Độ (Longitude)</label>
                    <input
                      type="text"
                      required
                      value={lng}
                      onChange={(e) => setLng(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-700 rounded text-white text-xs font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowModal(false)}
                >
                  Hủy Bỏ
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  loading={actionLoading === 'save_poi'}
                >
                  {isEditing ? 'Lưu Thay Đổi' : 'Thêm Địa Điểm'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Multilingual Detail & Audio Preview Modal */}
      {multilingualModalOpen && selectedPoiForMulti && (
        <Modal
          isOpen={multilingualModalOpen}
          onClose={() => {
            stopMultilingualAudio();
            setMultilingualModalOpen(false);
          }}
          maxWidth="2xl"
          title={
            <div>
              <h3 className="text-base font-semibold text-white">
                Chi Tiết & Nghe Thuyết Minh 6 Ngôn Ngữ
              </h3>
              <p className="text-xs text-slate-400">
                {selectedPoiForMulti.name}
              </p>
            </div>
          }
        >
          <div className="space-y-4">
            {/* Language Selector Tabs */}
            <div className="flex items-center gap-1 p-1 bg-slate-950 rounded border border-slate-800 overflow-x-auto">
              {[
                { code: 'vi' as const, flag: '🇻🇳', label: 'Tiếng Việt' },
                { code: 'en' as const, flag: '🇬🇧', label: 'English' },
                { code: 'fr' as const, flag: '🇫🇷', label: 'Français' },
                { code: 'ja' as const, flag: '🇯🇵', label: '日本語' },
                { code: 'ko' as const, flag: '🇰🇷', label: '한국어' },
                { code: 'zh' as const, flag: '🇨🇳', label: '中文' },
              ].map(({ code, flag, label }) => {
                const isActive = activeLangTab === code;
                const hasAudio = !!(
                  selectedPoiForMulti.translations?.[code]?.audio_url ||
                  selectedPoiForMulti.published_contents?.[code]?.audio_url ||
                  (code === 'vi' && selectedPoiForMulti.audio_url)
                );

                return (
                  <button
                    key={code}
                    type="button"
                    onClick={() => {
                      stopMultilingualAudio();
                      setActiveLangTab(code);
                    }}
                    className={`flex-1 min-w-[80px] py-1.5 px-2 rounded-sm text-xs font-medium flex items-center justify-center space-x-1 transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-indigo-600 text-white'
                        : 'text-slate-400 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <span>{flag}</span>
                    <span>{label}</span>
                    {hasAudio && (
                      <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-emerald-300' : 'bg-emerald-500'}`} />
                    )}
                  </button>
                );
              })}
            </div>

            {/* Language Content Display */}
            {(() => {
              const langData =
                selectedPoiForMulti.translations?.[activeLangTab] ||
                selectedPoiForMulti.published_contents?.[activeLangTab] ||
                (activeLangTab === 'vi' ? {
                  name: selectedPoiForMulti.name,
                  description: selectedPoiForMulti.description,
                  audio_url: selectedPoiForMulti.audio_url,
                  audio_duration_ms: selectedPoiForMulti.audio_duration_ms
                } : null);

              const poiId = selectedPoiForMulti.id || selectedPoiForMulti._id;
              const rawAudioUrl =
                langData?.audio_url ||
                `/storage/audio/${poiId}_${activeLangTab}.mp3`;
              const playUrl = rawAudioUrl.includes('?') ? `${rawAudioUrl}&t=${Date.now()}` : `${rawAudioUrl}?t=${Date.now()}`;

              return (
                <div className="space-y-3">
                  {/* Name Card */}
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 space-y-1">
                    <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                      Tiêu Đề ({activeLangTab.toUpperCase()})
                    </span>
                    <h4 className="text-sm font-semibold text-white">
                      {langData?.name || selectedPoiForMulti.name}
                    </h4>
                  </div>

                  {/* Description Card */}
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 space-y-1">
                    <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                      Nội Dung Thuyết Minh
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed max-h-40 overflow-y-auto pr-1 whitespace-pre-line">
                      {langData?.description || (
                        <span className="text-slate-500 italic">
                          Chưa có bản dịch cho ngôn ngữ này. Hãy bấm nút "Tạo Lại TTS" hoặc "Dịch 6 Thứ Tiếng".
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Audio Player Card */}
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-xs font-medium text-white">
                          Thuyết Minh Google TTS ({activeLangTab.toUpperCase()})
                        </span>
                        <p className="text-[10px] text-slate-400 font-mono">
                          {rawAudioUrl}
                        </p>
                      </div>

                      {/* Play / Pause Button */}
                      <div className="flex items-center space-x-2">
                        {isPlayingMultiAudio ? (
                          <button
                            type="button"
                            onClick={stopMultilingualAudio}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition-colors"
                          >
                            <Pause className="w-3.5 h-3.5" />
                            <span>Tạm Dừng</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => playMultilingualAudio(playUrl)}
                            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-medium transition-colors"
                          >
                            <Play className="w-3.5 h-3.5" />
                            <span>Nghe Thử</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Audio Native Controls */}
                    <audio
                      controls
                      src={playUrl}
                      className="w-full h-8 pt-1"
                      onPlay={() => setIsPlayingMultiAudio(true)}
                      onPause={() => setIsPlayingMultiAudio(false)}
                      onEnded={() => setIsPlayingMultiAudio(false)}
                    />
                  </div>

                  {/* Re-generate & Gemini Multilingual Buttons */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
                    <span className="text-xs text-slate-500">
                      Bản dịch hoặc audio bị lỗi?
                    </span>

                    <div className="flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={() => handleGeminiMultilingualTranslate(poiId)}
                        disabled={aiTranslatingMulti}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors disabled:opacity-50"
                        title="Dịch chuẩn ẩm thực và bản địa hóa 6 ngôn ngữ bằng Gemini AI"
                      >
                        <Sparkles className={`w-3.5 h-3.5 ${aiTranslatingMulti ? 'animate-spin' : ''}`} />
                        <span>{aiTranslatingMulti ? 'Đang dịch...' : 'Dịch 6 Thứ Tiếng'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleRecreateLanguageTTS(poiId, activeLangTab)}
                        disabled={recreatingLang === activeLangTab}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition-colors disabled:opacity-50"
                        title={`Tạo lại file giọng đọc Google TTS cho tab ${activeLangTab.toUpperCase()}`}
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${recreatingLang === activeLangTab ? 'animate-spin' : ''}`} />
                        <span>{recreatingLang === activeLangTab ? 'Đang tạo lại...' : `Tạo Lại TTS (${activeLangTab.toUpperCase()})`}</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        </Modal>
      )}
    </div>
  );
};
