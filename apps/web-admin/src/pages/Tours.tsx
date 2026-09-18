import React, { useEffect, useState } from 'react';
import { Route, MapPin, Plus, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';

export const Tours: React.FC = () => {
  const { token } = useAuth();
  const [tours, setTours] = useState<any[]>([]);
  const [selectedTour, setSelectedTour] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTours = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/tours'));
      const data = await res.json();
      setTours(Array.isArray(data) ? data : []);
      if (data.length > 0) {
        fetchTourDetail(data[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTourDetail = async (tourId: string) => {
    try {
      const res = await fetch(apiUrl(`/tours/${tourId}`));
      const data = await res.json();
      setSelectedTour(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchTours();
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Quản Lý Tuyến Du Lịch (Tours)</h1>
        <p className="text-sm text-slate-400 mt-1">
          Lộ trình tham quan có hướng dẫn và danh sách điểm dừng theo thứ tự (T12, T13, C15)
        </p>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400">Đang tải danh sách tour...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Tours List */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Danh Sách Tour ({tours.length})
            </h2>
            {tours.map((t) => (
              <div
                key={t.id}
                onClick={() => fetchTourDetail(t.id)}
                className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                  selectedTour?.id === t.id
                    ? 'bg-slate-900 border-indigo-500/80 shadow-lg shadow-indigo-500/10'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center space-x-2 text-indigo-400 mb-1">
                  <Route className="w-4 h-4" />
                  <span className="text-xs font-semibold">{t.poi_count} điểm dừng</span>
                </div>
                <h3 className="font-bold text-white text-base">{t.name}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{t.description}</p>
              </div>
            ))}
          </div>

          {/* Tour Stops Detail */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6">
            {selectedTour ? (
              <div className="space-y-6">
                <div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 uppercase">
                    Tour Đang Chọn
                  </span>
                  <h2 className="text-xl font-bold text-white mt-2">{selectedTour.name}</h2>
                  <p className="text-sm text-slate-400 mt-1">{selectedTour.description}</p>
                </div>

                <div className="border-t border-slate-800 pt-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">
                    Thứ Tự Các Điểm Dừng (Stops Order)
                  </h3>

                  <div className="space-y-3">
                    {selectedTour.pois?.map((p: any, index: number) => (
                      <div
                        key={p.id}
                        className="flex items-center space-x-4 p-4 rounded-xl bg-slate-950 border border-slate-800"
                      >
                        <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-400 font-bold flex items-center justify-center shrink-0 border border-indigo-500/30">
                          {index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-bold text-white text-sm truncate">{p.name}</h4>
                          <p className="text-xs text-slate-400 truncate">{p.address || 'Quận 4'}</p>
                        </div>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 capitalize">
                          {p.category}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-slate-500">
                Chọn một tour ở bên trái để xem chi tiết các điểm dừng.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
