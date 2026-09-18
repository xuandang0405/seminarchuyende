import React, { useEffect, useState } from 'react';
import { 
  Plus, 
  Search, 
  MapPin, 
  Headphones, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Volume2, 
  Trash2,
  ExternalLink,
  Sparkles,
  Clock
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';

export const POIList: React.FC = () => {
  const { token, user } = useAuth();
  const [pois, setPois] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modal create POI
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [address, setAddress] = useState('');
  const [cat, setCat] = useState('sightseeing');
  const [lng, setLng] = useState('106.702');
  const [lat, setLat] = useState('10.762');
  const [radius, setRadius] = useState('30.0');
  const [priority, setPriority] = useState('1');

  const fetchPOIs = async () => {
    setLoading(true);
    try {
      let endpoint = `/pois?limit=100`;
      if (search) endpoint += `&search=${encodeURIComponent(search)}`;
      if (category) endpoint += `&category=${encodeURIComponent(category)}`;

      const res = await fetch(apiUrl(endpoint));
      const data = await res.json();
      setPois(data.items || []);
    } catch (err) {
      console.error(err);
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

  const handleCreatePOI = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('create');
    setMessage(null);

    try {
      const res = await fetch(apiUrl('/pois'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name,
          description,
          category: cat,
          address,
          location: {
            type: 'Point',
            coordinates: [parseFloat(lng), parseFloat(lat)]
          },
          trigger_radius: parseFloat(radius),
          audio_priority: parseInt(priority, 10),
          activation_requested: false
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Không thể tạo POI');

      setMessage({ type: 'success', text: `Tạo địa điểm "${name}" thành công!` });
      setShowCreateModal(false);
      setName('');
      setDescription('');
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleGenerateTTS = async (poiId: string, lang: string = 'vi') => {
    setActionLoading(`tts_${poiId}`);
    setMessage(null);
    try {
      const res = await fetch(apiUrl(`/audio/generate/${poiId}`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ lang })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Tạo giọng đọc thất bại');

      setMessage({ type: 'success', text: `Đã tạo xong thuyết minh Edge-TTS (${lang}) cho địa điểm!` });
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleActive = async (poiId: string, currentActive: boolean) => {
    setActionLoading(`toggle_${poiId}`);
    setMessage(null);
    try {
      const res = await fetch(apiUrl(`/pois/${poiId}/toggle-active?active=${!currentActive}`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.gate_passed === false) {
        setMessage({
          type: 'error',
          text: `Readiness Gate: ${data.message} Lý do: ${data.reasons.join('; ')}`
        });
      } else {
        setMessage({ type: 'success', text: data.message });
      }
      fetchPOIs();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Danh Sách Địa Điểm Thuyết Minh (POIs)</h1>
          <p className="text-sm text-slate-400 mt-1">
            Quản lý tọa độ địa lý, bán kính kích hoạt GPS và thuyết minh đa ngôn ngữ Quận 4
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Địa Điểm Mới</span>
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-xl text-sm font-medium flex items-center space-x-2 ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm theo tên hoặc địa chỉ..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
          />
        </form>

        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-300 text-sm focus:outline-none focus:border-indigo-500"
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
        <div className="text-center py-16 text-slate-400 font-medium">Đang tải danh sách POI...</div>
      ) : pois.length === 0 ? (
        <div className="text-center py-16 text-slate-400">Không tìm thấy địa điểm nào phù hợp.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {pois.map((poi) => (
            <div key={poi.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between hover:border-slate-700 transition-all">
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <span className="px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 text-xs font-semibold capitalize">
                    {poi.category}
                  </span>
                  <div className="flex items-center space-x-1.5">
                    <span className="text-xs text-slate-400 font-mono">r={poi.trigger_radius}m</span>
                    {poi.is_active ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium">
                        <CheckCircle className="w-3 h-3" />
                        <span>Công bố</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 text-xs font-medium">
                        <Clock className="w-3 h-3" />
                        <span>Bản nháp</span>
                      </span>
                    )}
                  </div>
                </div>

                <h3 className="text-base font-bold text-white line-clamp-1">{poi.name}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{poi.description}</p>
                <p className="text-xs text-slate-500 mt-2 flex items-center space-x-1">
                  <MapPin className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{poi.address || 'Quận 4, TP.HCM'}</span>
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
                <div className="flex items-center space-x-1">
                  {poi.audio_url ? (
                    <span className="text-xs text-emerald-400 flex items-center space-x-1">
                      <Headphones className="w-3.5 h-3.5" />
                      <span>{Math.round(poi.audio_duration_ms / 1000)}s</span>
                    </span>
                  ) : (
                    <span className="text-xs text-slate-500">Chưa có audio</span>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleGenerateTTS(poi.id, 'vi')}
                    disabled={actionLoading === `tts_${poi.id}`}
                    title="Tạo giọng nói Edge-TTS"
                    className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-indigo-400 transition-colors disabled:opacity-50"
                  >
                    <Volume2 className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleToggleActive(poi.id, poi.is_active)}
                    disabled={actionLoading === `toggle_${poi.id}`}
                    className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                      poi.is_active
                        ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                    }`}
                  >
                    {poi.is_active ? 'Ẩn' : 'Công Bố'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Create POI */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-xl shadow-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-white mb-4">Thêm Địa Điểm Du Lịch Mới</h2>
            <form onSubmit={handleCreatePOI} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Tên Địa Điểm</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Bến Nhà Rồng - Bảo Tàng Hồ Chí Minh"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mô Tả Chi Tiết</label>
                <textarea
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Nội dung thuyết minh lịch sử, văn hóa hoặc điểm đặc sắc..."
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Danh Mục</label>
                  <select
                    value={cat}
                    onChange={(e) => setCat(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                  >
                    <option value="sightseeing">Cảnh quan</option>
                    <option value="historical">Di tích lịch sử</option>
                    <option value="food">Ẩm thực</option>
                    <option value="culture">Văn hóa</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Bán Kính GPS (mét)</label>
                  <input
                    type="number"
                    value={radius}
                    onChange={(e) => setRadius(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Địa Chỉ</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Số 01 Nguyễn Tất Thành, Phường 12, Quận 4"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Kinh Độ (Longitude)</label>
                  <input
                    type="text"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Vĩ Độ (Latitude)</label>
                  <input
                    type="text"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === 'create'}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30"
                >
                  {actionLoading === 'create' ? 'Đang tạo...' : 'Lưu Địa Điểm'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
