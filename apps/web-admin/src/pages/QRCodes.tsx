import React, { useEffect, useState } from 'react';
import { QrCode, Plus, CheckCircle2, AlertCircle, Ban } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';

export const QRCodes: React.FC = () => {
  const { token, user } = useAuth();
  const [pois, setPois] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [selectedPoiId, setSelectedPoiId] = useState('');
  const [code, setCode] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Sample seeded QR codes
  const [sampleQrs, setSampleQrs] = useState<any[]>([
    { id: 'qr_ben_nha_rong_01', code: 'Q4-BNR-01', poi_id: 'poi_ben_nha_rong', poi_name: 'Bến Nhà Rồng - Bảo tàng Hồ Chí Minh', is_active: true },
    { id: 'qr_vinh_khanh_01', code: 'Q4-VKH-01', poi_id: 'poi_pho_oc_vinh_khanh', poi_name: 'Phố Ẩm Thực Vĩnh Khánh', is_active: true },
    { id: 'qr_cau_mong_01', code: 'Q4-CMG-01', poi_id: 'poi_cau_mong', poi_name: 'Cầu Mống', is_active: true },
  ]);

  useEffect(() => {
    fetch(apiUrl('/pois?limit=100'))
      .then((r) => r.json())
      .then((data) => {
        setPois(data.items || []);
        if (data.items?.length > 0) setSelectedPoiId(data.items[0].id);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCreateQR = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      const res = await fetch(apiUrl('/qr'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ poi_id: selectedPoiId, code })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Tạo mã QR thất bại');

      const poiObj = pois.find((p) => p.id === selectedPoiId);
      setSampleQrs([
        ...sampleQrs,
        {
          id: data._id,
          code: data.code,
          poi_id: selectedPoiId,
          poi_name: poiObj ? poiObj.name : selectedPoiId,
          is_active: true
        }
      ]);
      setMessage({ type: 'success', text: `Tạo mã QR "${code}" thành công!` });
      setShowModal(false);
      setCode('');
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const handleDeactivate = async (qrId: string) => {
    try {
      await fetch(apiUrl(`/qr/${qrId}/deactivate`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      setSampleQrs(sampleQrs.map((q) => q.id === qrId ? { ...q, is_active: false } : q));
      setMessage({ type: 'success', text: 'Đã vô hiệu hóa mã QR.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Quản Lý Mã QR Thuyết Minh (T11, C16)</h1>
          <p className="text-sm text-slate-400 mt-1">
            Gắn mã QR tại các bảng chỉ dẫn hoặc bàn ăn để du khách quét nghe thuyết minh không cần bật GPS
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Tạo Mã QR Mới</span>
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-xl text-sm font-medium flex items-center space-x-2 ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          {message.type === 'success' ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* QR Codes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {sampleQrs.map((qr) => (
          <div key={qr.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center text-indigo-400">
                  <QrCode className="w-6 h-6" />
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                  qr.is_active ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {qr.is_active ? 'Đang hiệu lực' : 'Đã vô hiệu'}
                </span>
              </div>

              <span className="font-mono text-xs font-bold text-indigo-400 tracking-wider bg-indigo-500/10 px-2.5 py-1 rounded-md">
                {qr.code}
              </span>
              <h3 className="text-base font-bold text-white mt-3 line-clamp-1">{qr.poi_name}</h3>
              <p className="text-xs text-slate-500 mt-1">POI ID: {qr.poi_id}</p>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">Quét test: /qr/{qr.code}</span>
              {qr.is_active && (
                <button
                  onClick={() => handleDeactivate(qr.id)}
                  className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs font-medium transition-colors flex items-center space-x-1"
                >
                  <Ban className="w-3.5 h-3.5" />
                  <span>Vô hiệu</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-4">Tạo Mã QR Mới</h2>
            <form onSubmit={handleCreateQR} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Chọn POI</label>
                <select
                  value={selectedPoiId}
                  onChange={(e) => setSelectedPoiId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                >
                  {pois.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mã Code (Opaque)</label>
                <input
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Q4-MYPOI-01"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm font-mono"
                />
              </div>

              <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30"
                >
                  Lưu Mã QR
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
