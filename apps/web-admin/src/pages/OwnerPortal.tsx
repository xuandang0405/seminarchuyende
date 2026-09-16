import React, { useEffect, useState } from 'react';
import { Store, Send, Bell, Plus, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const OwnerPortal: React.FC = () => {
  const { token, user } = useAuth();
  const [pois, setPois] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Draft form state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [address, setAddress] = useState('');
  const [lng, setLng] = useState('106.700');
  const [lat, setLat] = useState('10.760');
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [poisRes, subsRes, notifsRes] = await Promise.all([
        fetch('/api/v1/owner/pois', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/owner/submissions', { headers: { Authorization: `Bearer ${token}` } }),
        fetch('/api/v1/owner/notifications', { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      const [poisData, subsData, notifsData] = await Promise.all([
        poisRes.json(),
        subsRes.json(),
        notifsRes.json(),
      ]);

      setPois(Array.isArray(poisData) ? poisData : []);
      setSubmissions(Array.isArray(subsData) ? subsData : []);
      setNotifications(Array.isArray(notifsData) ? notifsData : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const handleSubmitDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    setMessage(null);

    try {
      const res = await fetch('/api/v1/owner/submissions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: 'create',
          payload: {
            name,
            description,
            category: 'food',
            address,
            location: {
              type: 'Point',
              coordinates: [parseFloat(lng), parseFloat(lat)],
            },
            trigger_radius: 30.0,
            audio_priority: 5,
          },
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || data.error || 'Gửi thất bại.');

      setMessage({ type: 'success', text: 'Đề xuất POI mới đã được gửi thành công tới Admin!' });
      setShowSubmitModal(false);
      setName('');
      setDescription('');
      fetchData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Cổng Dành Cho Chủ Quán Ẩm Thực (Owner Portal)</h1>
          <p className="text-sm text-slate-400 mt-1">
            Quản lý địa điểm của quán, gửi đề xuất nội dung và theo dõi thông báo xét duyệt
          </p>
        </div>

        <button
          onClick={() => setShowSubmitModal(true)}
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Đề Xuất POI Mới</span>
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

      {/* Grid: My POIs & Notifications */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: My POIs & Submissions */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center space-x-2">
              <Store className="w-5 h-5 text-indigo-400" />
              <span>Quán Đang Hoạt Động Của Tôi ({pois.length})</span>
            </h2>

            {pois.length === 0 ? (
              <p className="text-sm text-slate-500 py-6 text-center">
                Bạn chưa có địa điểm nào được công bố. Hãy gửi đề xuất nội dung mới!
              </p>
            ) : (
              <div className="space-y-3">
                {pois.map((p) => (
                  <div key={p._id} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-white text-sm">{p.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{p.address || 'Quận 4, TP.HCM'}</p>
                    </div>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">
                      Đã công bố
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center space-x-2">
              <Send className="w-5 h-5 text-amber-400" />
              <span>Lịch Sử Đề Xuất Duyệt Nội Dung ({submissions.length})</span>
            </h2>

            {submissions.length === 0 ? (
              <p className="text-sm text-slate-500 py-6 text-center">Chưa có đề xuất nào gửi duyệt.</p>
            ) : (
              <div className="space-y-3">
                {submissions.map((s) => (
                  <div key={s._id} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-white text-sm">{s.payload?.name || 'Đề xuất'}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Ngày gửi: {new Date(s.created_at).toLocaleDateString('vi-VN')}
                      </p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      s.status === 'approved'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : s.status === 'rejected'
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-amber-500/10 text-amber-400'
                    }`}>
                      {s.status === 'approved' ? 'Đã duyệt' : s.status === 'rejected' ? 'Từ chối' : 'Chờ duyệt'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: In-App Notifications */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h2 className="text-base font-bold text-white mb-4 flex items-center space-x-2">
            <Bell className="w-5 h-5 text-indigo-400" />
            <span>Thông Báo Của Tôi ({notifications.length})</span>
          </h2>

          {notifications.length === 0 ? (
            <p className="text-sm text-slate-500 py-12 text-center">Chưa có thông báo nào.</p>
          ) : (
            <div className="space-y-3">
              {notifications.map((n) => (
                <div key={n._id} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs">
                  <p className="text-slate-200 font-medium">{n.message}</p>
                  <p className="text-slate-500 mt-1">
                    {new Date(n.created_at).toLocaleString('vi-VN')}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modal Submit POI Draft */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-lg shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-4">Gửi Đề Xuất Quán Ăn Mới Tới Admin</h2>
            <form onSubmit={handleSubmitDraft} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Tên Quán</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Quán Ốc Đêm Vĩnh Khánh"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mô Tả Đặc Sắc</label>
                <textarea
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Món ăn đặc sản, hải sản tươi sống và không gian quán..."
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Địa Chỉ</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="123 Vĩnh Khánh, Quận 4, TP.HCM"
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm"
                />
              </div>

              <div className="flex justify-end space-x-3 mt-6 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowSubmitModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30"
                >
                  {actionLoading ? 'Đang gửi...' : 'Gửi Phê Duyệt'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
