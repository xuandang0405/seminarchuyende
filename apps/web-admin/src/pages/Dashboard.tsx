import React, { useEffect, useState } from 'react';
import { 
  MapPin, 
  Headphones, 
  Clock, 
  TrendingUp, 
  RefreshCw,
  Award
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Dashboard: React.FC = () => {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/analytics/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [token]);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {user?.role === 'poi_owner' ? 'Thống Kê Quán Của Tôi' : 'Bảng Điều Khiển Tổng Quan'}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Số liệu thống kê lượt nghe thuyết minh và hoạt động du lịch tại Quận 4
          </p>
        </div>
        <button
          onClick={fetchStats}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 rounded-xl text-sm font-medium transition-all"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          <span>Làm mới</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {user?.role === 'poi_owner' ? 'Địa Điểm Quản Lý' : 'Địa Điểm Hoạt Động'}
            </span>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <MapPin className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-4">
            {stats ? (stats.total_active_pois ?? stats.total_pois ?? 0) : '--'}
          </p>
          <p className="text-xs text-slate-400 mt-2">Đã được duyệt & sẵn sàng</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Lượt Nghe Audio</span>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <Headphones className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-4">
            {stats ? (stats.total_audio_plays ?? stats.audio_plays ?? 0) : '--'}
          </p>
          <p className="text-xs text-slate-400 mt-2">Khử trùng lặp theo playback_id</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Tổng Giờ Nghe</span>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-4">
            {stats ? (stats.total_listen_hours ?? 0) : '--'} <span className="text-lg font-normal text-slate-400">giờ</span>
          </p>
          <p className="text-xs text-slate-400 mt-2">Thời gian nghe thực tế</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Thời Lượng TB / Lần</span>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-4">
            {stats ? (stats.avg_listen_duration_seconds ?? 0) : '--'} <span className="text-lg font-normal text-slate-400">giây</span>
          </p>
          <p className="text-xs text-slate-400 mt-2">Mẫu số chuẩn không chia cho 0</p>
        </div>
      </div>

      {/* Top POIs Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center space-x-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <Award className="w-4 h-4" />
          </div>
          <h2 className="text-lg font-bold text-white">Điểm Thuyết Minh Hàng Đầu (Top POIs)</h2>
        </div>

        {stats?.top_pois && stats.top_pois.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">#</th>
                  <th className="py-3.5 px-4">Tên Địa Điểm</th>
                  <th className="py-3.5 px-4">Lượt Nghe Thành Công</th>
                  <th className="py-3.5 px-4">Tổng Thời Gian (Phút)</th>
                  <th className="py-3.5 px-4">Thời Lượng TB</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {stats.top_pois.map((poi: any, idx: number) => (
                  <tr key={poi.poi_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-indigo-400">{idx + 1}</td>
                    <td className="py-3.5 px-4 font-medium text-white">{poi.poi_name || poi.poi_id}</td>
                    <td className="py-3.5 px-4">{poi.audio_plays ?? poi.plays ?? 0} lượt</td>
                    <td className="py-3.5 px-4">{poi.total_minutes ?? poi.minutes ?? 0} phút</td>
                    <td className="py-3.5 px-4">{poi.avg_duration_seconds ?? '--'}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-400">
            Chưa có đủ dữ liệu sự kiện phát để xếp hạng top POI.
          </div>
        )}
      </div>
    </div>
  );
};
