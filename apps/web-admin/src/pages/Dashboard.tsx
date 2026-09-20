import React, { useEffect, useState } from 'react';
import { 
  MapPin, 
  Headphones, 
  Clock, 
  TrendingUp, 
  RefreshCw,
  Award,
  Smartphone,
  Users,
  Route,
  Activity,
  Calendar,
  DollarSign,
  QrCode,
  Globe,
  CreditCard,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';
import { Badge, Button, PageHeader } from '../components/ui';

export const Dashboard: React.FC = () => {
  const { token, user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [topPois, setTopPois] = useState<any[]>([]);
  const [tourStats, setTourStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    setLoading(true);
    try {
      if (user?.role === 'poi_owner') {
        const res = await fetch(apiUrl('/analytics/dashboard'), {
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = await res.json();
        setStats(data);
      } else {
        // Admin: fetch overview, top POIs, and tours
        const [overviewRes, poisRes, toursRes] = await Promise.all([
          fetch(apiUrl('/analytics/overview'), {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(apiUrl('/analytics/pois?limit=50'), {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(apiUrl('/analytics/tours'), {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);

        if (overviewRes.ok) {
          const overviewData = await overviewRes.json();
          setStats(overviewData);
        }
        if (poisRes.ok) {
          const poisData = await poisRes.json();
          setTopPois(Array.isArray(poisData) ? poisData : []);
        }
        if (toursRes.ok) {
          const toursData = await toursRes.json();
          setTourStats(Array.isArray(toursData) ? toursData : []);
        }
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [token, user?.role]);

  const formatVND = (amount: number) => {
    return (amount || 0).toLocaleString('vi-VN') + ' đ';
  };

  const getLanguageName = (code: string) => {
    const map: Record<string, string> = {
      vi: '🇻🇳 Tiếng Việt',
      en: '🇬🇧 English',
      ja: '🇯🇵 日本語',
      ko: '🇰🇷 한국어',
      zh: '🇨🇳 中文',
      fr: '🇫🇷 Français'
    };
    return map[code] || code.toUpperCase();
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 space-y-8 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Unified Page Header */}
      <PageHeader
        title={user?.role === 'poi_owner' ? 'Thống Kê Điểm Đến Của Tôi' : 'Bảng Điều Khiển & Thống Kê Du Lịch'}
        badge={<Badge variant="success" size="sm" showDot>Live Realtime</Badge>}
        description="Tổng hợp dữ liệu bán vé, khách truy cập trực tuyến, thiết bị di động và lượt nghe thuyết minh Quận 4"
        actions={
          <div className="flex items-center space-x-2.5">
            {stats?.data_freshness_watermark && (
              <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
                <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                <span>{new Date(stats.data_freshness_watermark).toLocaleTimeString('vi-VN')}</span>
              </div>
            )}
            <Button
              variant="secondary"
              size="md"
              onClick={fetchStats}
              loading={loading}
              icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />}
            >
              Làm mới
            </Button>
          </div>
        }
      />

      {/* 4 Big Main KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Total Revenue */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-emerald-500/20 hover:border-emerald-500/40 rounded-2xl p-6 relative overflow-hidden transition-all shadow-lg group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl group-hover:bg-emerald-500/10 transition-all"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {user?.role === 'poi_owner' ? 'Doanh Thu Ước Tính' : 'Tổng Tiền Bán Vé Tour'}
            </span>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-4 tracking-tight">
            {stats ? formatVND(stats.total_revenue_vnd || 0) : '--'}
          </p>
          <div className="mt-2.5 flex items-center text-xs text-slate-400 gap-1.5">
            <span className="font-semibold text-emerald-400">{stats?.paid_orders_count || 0} vé đã thanh toán</span>
            <span>•</span>
            <span>{stats?.pending_orders_count || 0} đang chờ</span>
          </div>
        </div>

        {/* Active Now & Users */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-blue-500/20 hover:border-blue-500/40 rounded-2xl p-6 relative overflow-hidden transition-all shadow-lg group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl group-hover:bg-blue-500/10 transition-all"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {user?.role === 'poi_owner' ? 'Khách Đang Tham Quan' : 'Khách Đang Dùng (15p)'}
            </span>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center border border-blue-500/20">
              <Activity className="w-5 h-5 animate-pulse text-blue-400" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mt-4">
            <p className="text-3xl font-extrabold text-blue-400 tracking-tight">
              {stats ? (stats.active_visitor_sessions_now || 0) : '--'}
            </p>
            <span className="text-xs font-medium text-slate-400">người trực tiếp</span>
          </div>
          <div className="mt-2.5 flex items-center text-xs text-slate-400 gap-1.5">
            <span className="font-semibold text-slate-300">{stats?.total_registered_users || 0} tài khoản du khách</span>
            <span>•</span>
            <span>{stats?.unique_devices_count || 0} thiết bị</span>
          </div>
        </div>

        {/* Total Audio Narration Plays */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-purple-500/20 hover:border-purple-500/40 rounded-2xl p-6 relative overflow-hidden transition-all shadow-lg group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl group-hover:bg-purple-500/10 transition-all"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Tổng Lượt Nghe Thuyết Minh
            </span>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
              <Headphones className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mt-4">
            <p className="text-3xl font-extrabold text-white tracking-tight">
              {stats ? (stats.listen_started_count ?? stats.total_audio_plays ?? 0).toLocaleString('vi-VN') : '--'}
            </p>
            <span className="text-xs font-medium text-purple-300">lượt nghe</span>
          </div>
          <div className="mt-2.5 flex items-center text-xs text-slate-400 gap-1.5">
            <span className="font-semibold text-purple-400">{stats?.total_listen_hours || 0} giờ nghe</span>
            <span>•</span>
            <span>Tỷ lệ hoàn thành: {stats?.listen_completion_rate_percent || 0}%</span>
          </div>
        </div>

        {/* Tourism Infrastructure & QR */}
        <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-amber-500/20 hover:border-amber-500/40 rounded-2xl p-6 relative overflow-hidden transition-all shadow-lg group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl group-hover:bg-amber-500/10 transition-all"></div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Địa Điểm & Tuyến Tour
            </span>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
              <MapPin className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mt-4">
            <p className="text-3xl font-extrabold text-white tracking-tight">
              {stats ? (stats.total_pois_count ?? stats.total_active_pois ?? 0) : '--'}
            </p>
            <span className="text-xs font-medium text-amber-300">địa điểm POI</span>
          </div>
          <div className="mt-2.5 flex items-center text-xs text-slate-400 gap-1.5">
            <span className="font-semibold text-amber-400">{stats?.total_tours_count || 10} tuyến tour</span>
            <span>•</span>
            <span>{stats?.total_qr_scans || 0} lượt quét QR</span>
          </div>
        </div>
      </div>

      {/* Ticket Revenue by Tour (Admin View) */}
      {user?.role !== 'poi_owner' && stats?.revenue_by_tour && stats.revenue_by_tour.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
                <CreditCard className="w-4 h-4" />
              </div>
              <h2 className="text-lg font-bold text-white">Doanh Thu Theo Tuyến Tour Du Lịch</h2>
            </div>
            <span className="text-xs font-medium text-slate-400">
              Cập nhật từ hệ thống thanh toán PayOS
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.revenue_by_tour.map((t: any, index: number) => (
              <div 
                key={t.tour_id || index}
                className="bg-slate-950/70 border border-slate-800 hover:border-slate-700 p-4 rounded-xl flex flex-col justify-between transition-all"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-white text-sm line-clamp-1">{t.title || t.tour_id}</h3>
                    <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                      {t.paid_orders} vé
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Mã gói: <span className="font-mono text-slate-300">{t.tour_id}</span></p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-baseline justify-between">
                  <span className="text-xs text-slate-400">Doanh thu thu về:</span>
                  <span className="text-lg font-bold text-emerald-400">{formatVND(t.revenue_vnd)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* POI Listening Performance Table (All POIs Ranked) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
              <Award className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Thống Kê Lượt Nghe Chi Tiết Từng Địa Điểm (POI)</h2>
              <p className="text-xs text-slate-400">Xếp hạng theo số lượt du khách nghe bài thuyết minh tại Quận 4</p>
            </div>
          </div>
          <span className="text-xs text-slate-400">
            Tổng cộng: <strong className="text-white">{topPois.length}</strong> địa điểm
          </span>
        </div>

        {topPois.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/70 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4 w-12 text-center">#</th>
                  <th className="py-3.5 px-4">Tên Địa Điểm / Quán Ăn</th>
                  <th className="py-3.5 px-4 text-center">Bắt Đầu Nghe</th>
                  <th className="py-3.5 px-4 text-center">Nghe Hết</th>
                  <th className="py-3.5 px-4 text-center">Tỷ Lệ Hoàn Thành</th>
                  <th className="py-3.5 px-4 text-center">Thời Lượng TB</th>
                  <th className="py-3.5 px-4 text-center">Thiết Bị Độc Lập</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {topPois.map((poi: any, idx: number) => {
                  const started = poi.listen_started_count ?? poi.plays ?? 0;
                  const completed = poi.listen_completed_count ?? 0;
                  const compRate = poi.completion_rate_percent ?? (started > 0 ? Math.round((completed / started) * 100) : 0);
                  
                  return (
                    <tr key={poi.poi_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3.5 px-4 text-center">
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                          idx === 0 ? 'bg-amber-500 text-slate-950' :
                          idx === 1 ? 'bg-slate-300 text-slate-950' :
                          idx === 2 ? 'bg-amber-700 text-white' :
                          'text-slate-400 bg-slate-800'
                        }`}>
                          {idx + 1}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{poi.poi_name || poi.name || poi.poi_id}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          Mã POI: <span className="font-mono text-slate-500">{poi.poi_id}</span>
                          {poi.category && (
                            <span className="ml-2 px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                              {poi.category}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-center font-semibold text-indigo-400">
                        {started.toLocaleString('vi-VN')} lượt
                      </td>
                      <td className="py-3.5 px-4 text-center text-emerald-400 font-semibold">
                        {completed.toLocaleString('vi-VN')} lượt
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-16 h-2 rounded-full bg-slate-800 overflow-hidden">
                            <div 
                              className="h-full bg-emerald-500 rounded-full" 
                              style={{ width: `${Math.min(100, Math.max(0, compRate))}%` }}
                            ></div>
                          </div>
                          <span className="text-xs font-semibold text-slate-200">{compRate}%</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-center text-slate-400">
                        {poi.avg_listen_duration_seconds ? `${poi.avg_listen_duration_seconds}s` : '--'}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-300 text-xs font-semibold border border-blue-500/20">
                          {poi.unique_devices || 0} thiết bị
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-400">
            Chưa có đủ dữ liệu sự kiện phát để xếp hạng POI.
          </div>
        )}
      </div>

      {/* Language Breakdown & Tourism Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Popular Languages */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center space-x-3 mb-5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
              <Globe className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Ngôn Ngữ Thuyết Minh Được Sử Dụng</h2>
              <p className="text-xs text-slate-400">Tỉ lệ lựa chọn ngôn ngữ từ du khách quốc tế và nội địa</p>
            </div>
          </div>

          <div className="space-y-3">
            {stats?.popular_languages && stats.popular_languages.length > 0 ? (
              stats.popular_languages.map((lang: any) => {
                const totalLang = stats.popular_languages.reduce((acc: number, cur: any) => acc + cur.count, 0);
                const pct = totalLang > 0 ? Math.round((lang.count / totalLang) * 100) : 0;
                return (
                  <div key={lang.code} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-base">{getLanguageName(lang.code)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${pct}%` }}></div>
                      </div>
                      <span className="text-xs font-bold text-white w-10 text-right">{pct}%</span>
                      <span className="text-xs text-slate-400">({lang.count} lượt)</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-6 text-slate-400 text-sm">
                Đang sử dụng mặc định Tiếng Việt và Tiếng Anh.
              </div>
            )}
          </div>
        </div>

        {/* Tour Sessions Performance (Admin View) */}
        {user?.role !== 'poi_owner' && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center space-x-3 mb-5">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
                <Route className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Thống Kê Tuyến Đi Bộ (Tour Sessions)</h2>
                <p className="text-xs text-slate-400">Hiệu suất và tỷ lệ hoàn thành hành trình tham quan</p>
              </div>
            </div>

            {tourStats.length > 0 ? (
              <div className="space-y-3">
                {tourStats.slice(0, 4).map((tour: any) => (
                  <div key={tour.tour_id} className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h4 className="font-semibold text-white text-sm line-clamp-1">{tour.tour_name || tour.tour_id}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {tour.started_count || 0} lượt bắt đầu • {tour.completed_count || 0} lượt hoàn tất
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 text-xs font-semibold border border-emerald-500/20">
                        {tour.completion_rate_percent ?? 0}% hoàn thành
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-400 text-sm">
                Chưa có phiên tour hoàn tất trong hôm nay.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
export default Dashboard;
