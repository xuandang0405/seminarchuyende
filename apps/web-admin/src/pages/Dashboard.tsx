import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  RefreshCw,
  Calendar, MapPin, Store, ArrowUpRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../config/runtime';
import { Badge, Button, PageHeader } from '../components/ui';
import { HarborArt } from '../components/Brand';
import { languages } from '../../../../shared/brand';

interface DashboardSnapshot {
  overview: any;
  pois: any[];
  tours: any[];
}

function formatListeningTime(total: number) {
  const seconds = Math.floor(total);
  if (seconds < 60) return `${seconds} giây`;
  const minutes = Math.floor(seconds / 60);
  return minutes < 60 ? `${minutes} phút ${seconds % 60} giây` : `${Math.floor(minutes / 60)} giờ ${minutes % 60} phút`;
}

export const Dashboard: React.FC = () => {
  const { user, fetchWithAuth } = useAuth();
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>();
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);
  const [error, setError] = useState('');
  const fetching = useRef(false);
  const streamRevision = useRef(0);
  const stats = snapshot?.overview;
  const topPois = snapshot?.pois || [];
  const tourStats = snapshot?.tours || [];
  const owner = user?.role === 'poi_owner';

  const fetchStats = useCallback(async (manual = false) => {
    if (fetching.current) return;
    fetching.current = true;
    const revision = streamRevision.current;
    if (manual) setLoading(true);
    try {
      const response = await fetchWithAuth('/analytics/live-snapshot');
      if (!response.ok) throw new Error('Dashboard unavailable');
      const data: DashboardSnapshot = await response.json();
      if (revision === streamRevision.current) {
        setSnapshot(data);
        setError('');
      }
    } catch {
      if (revision === streamRevision.current) setError('Chưa lấy được số liệu mới. Đang thử kết nối lại.');
    } finally {
      fetching.current = false;
      setLoading(false);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    const source = new EventSource(apiUrl('/analytics/live'), { withCredentials: true });
    source.onmessage = event => {
      streamRevision.current++;
      setSnapshot(JSON.parse(event.data));
      setLoading(false);
      setLive(true);
      setError('');
    };
    source.onerror = () => {
      setLive(false);
      void fetchStats();
    };
    const fallback = window.setInterval(() => {
      if (source.readyState !== EventSource.OPEN) void fetchStats();
    }, 5000);
    void fetchStats();
    return () => { source.close(); window.clearInterval(fallback); };
  }, [fetchStats, user?.id]);

  const formatVND = (amount: number) => {
    return (amount || 0).toLocaleString('vi-VN') + ' đ';
  };

  const getLanguageName = (code: string) => {
    return languages.find(([language]) => language === code)?.[1] || code.toUpperCase();
  };

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      <section className="console-overview">
        <HarborArt />
        <p className="console-overview-kicker">TOURVOICE · QUẬN 4</p>
        <h1>{owner ? 'Cổng chủ cơ sở' : 'Không gian quản trị'}</h1>
        <p>{owner ? 'Theo dõi lượt nghe và cập nhật thông tin cơ sở của bạn.' : 'Quản lý điểm dừng, tuyến tham quan và vé từ một nơi.'}</p>
        <div className="console-overview-actions">
          <Button variant="secondary" onClick={() => navigate(owner ? '/owner' : '/pois')} icon={owner ? <Store size={17} /> : <MapPin size={17} />}>{owner ? 'Cơ sở của tôi' : 'Quản lý địa điểm'}</Button>
          <Button variant="outline" onClick={() => navigate('/client')} icon={<ArrowUpRight size={17} />}>Xem cẩm nang</Button>
        </div>
      </section>
      {/* Page Header */}
      <PageHeader
        title="Tổng quan hoạt động"
        badge={<Badge size="sm" variant={live ? 'success' : 'neutral'} showDot>{live ? 'Trực tiếp' : loading ? 'Đang tải' : 'Đang kết nối lại'}</Badge>}
        description={owner ? 'Lượt nghe tại các địa điểm thuộc cơ sở của bạn.' : 'Phiên web đang mở, lượt nghe và vé đã thanh toán.'}
        actions={
          <div className="flex items-center space-x-2">
            {stats?.data_freshness_watermark && (
              <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-xs text-slate-400">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>{new Date(stats.data_freshness_watermark).toLocaleTimeString('vi-VN')}</span>
              </div>
            )}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void fetchStats(true)}
              loading={loading}
              icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />}
            >
              Làm mới
            </Button>
          </div>
        }
      />

      {error && <div className="console-error" role="alert">{error}<Button variant="outline" size="sm" onClick={() => void fetchStats(true)}>Thử lại</Button></div>}
      <div className="stats-grid" aria-busy={loading}>
        {/* Total Revenue */}
        {!owner && <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Tiền bán vé tour
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {stats ? formatVND(stats.total_revenue_vnd || 0) : '--'}
          </p>
          <div className="mt-2 text-xs text-slate-400">
            <span className="text-emerald-400 font-medium">{stats?.paid_orders_count || 0} vé đã thanh toán</span>
            <span className="mx-1">•</span>
            <span>{stats?.pending_orders_count || 0} chờ</span>
          </div>
        </div>}

        {/* Active Now & Users */}
        {!owner && <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Phiên web đang mở
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <p data-stat="web-sessions" className="text-2xl font-bold text-blue-400">
              {stats ? stats.live_web_sessions : '—'}
            </p>
            <span className="text-xs text-slate-400">phiên cẩm nang</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            <span>{stats?.total_registered_users || 0} tài khoản</span>
            <span className="mx-1">•</span>
            <span>{stats?.unique_devices_count || 0} thiết bị đã đồng ý thống kê</span>
          </div>
        </div>}

        {/* Total Audio Narration Plays */}
        <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            Lượt Nghe Thuyết Minh
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <p data-stat="listen-started" className="text-2xl font-bold text-white">
              {stats ? (stats.listen_started_count ?? stats.total_audio_plays ?? 0).toLocaleString('vi-VN') : '--'}
            </p>
            <span className="text-xs text-slate-400">lượt</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            <span data-stat="listen-time">{formatListeningTime(stats?.total_listened_seconds ?? 0)} nghe</span>
            <span className="mx-1">•</span>
            <span data-stat="listen-completed">Hoàn thành: {stats?.listen_completion_rate_percent || 0}%</span>
          </div>
        </div>

        {/* Tourism Infrastructure & QR */}
        <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">
            {owner ? 'Địa điểm của cơ sở' : 'Địa điểm & tuyến tour'}
          </div>
          <div className="flex items-baseline gap-2 mt-2">
            <p className="text-2xl font-bold text-white">
              {stats ? (stats.total_pois_count ?? stats.total_active_pois ?? 0) : '--'}
            </p>
            <span className="text-xs text-slate-400">địa điểm POI</span>
          </div>
          {!owner && <div className="mt-2 text-xs text-slate-400">
            <span>{stats?.total_tours_count ?? '—'} tuyến tour</span>
            <span className="mx-1">•</span>
            <span>{stats?.total_qr_scans || 0} quét QR</span>
          </div>}
        </div>
      </div>

      {/* Ticket Revenue by Tour (Admin View) */}
      {user?.role !== 'poi_owner' && stats?.revenue_by_tour && stats.revenue_by_tour.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <h2 className="text-base font-semibold text-white">Doanh Thu Theo Tuyến Tour</h2>
            <span className="text-xs text-slate-400">Đơn đã xác nhận</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {stats.revenue_by_tour.map((t: any, index: number) => (
              <div 
                key={t.tour_id || index}
                className="bg-slate-950 border border-slate-800 p-3 rounded flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-medium text-white text-sm line-clamp-1">{t.title || t.tour_id}</h3>
                    <span className="px-1.5 py-0.2 rounded-sm text-[10px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 shrink-0">
                      {t.paid_orders} vé
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Mã gói: <span className="font-mono text-slate-300">{t.tour_id}</span></p>
                </div>
                <div className="mt-3 pt-2 border-t border-slate-800 flex items-baseline justify-between">
                  <span className="text-xs text-slate-400">Doanh thu:</span>
                  <span className="text-sm font-bold text-emerald-400">{formatVND(t.revenue_vnd)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* POI Listening Performance Table (All POIs Ranked) */}
      <div className="bg-slate-900 border border-slate-800 rounded p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-base font-semibold text-white">Thống Kê Lượt Nghe Từng Địa Điểm (POI)</h2>
            <p className="text-xs text-slate-400">Xếp hạng theo số lượt du khách nghe bài thuyết minh tại Quận 4</p>
          </div>
          <span className="text-xs text-slate-400">
            Tổng cộng: <strong className="text-white">{topPois.length}</strong> địa điểm
          </span>
        </div>

        {topPois.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950 text-xs uppercase font-medium text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3 w-10 text-center">#</th>
                  <th className="py-2.5 px-3">Tên Địa Điểm / Quán Ăn</th>
                  <th className="py-2.5 px-3 text-center">Bắt Đầu Nghe</th>
                  <th className="py-2.5 px-3 text-center">Nghe Hết</th>
                  <th className="py-2.5 px-3 text-center">Tỷ Lệ</th>
                  <th className="py-2.5 px-3 text-center">Thời Lượng TB</th>
                  <th className="py-2.5 px-3 text-center">Thiết Bị</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-normal">
                {topPois.map((poi: any, idx: number) => {
                  const started = poi.listen_started_count ?? poi.plays ?? 0;
                  const completed = poi.listen_completed_count ?? 0;
                  const compRate = poi.completion_rate_percent ?? (started > 0 ? Math.round((completed / started) * 100) : 0);
                  
                  return (
                    <tr key={poi.poi_id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-3 text-center">
                        <span className={`inline-flex items-center justify-center w-5 h-5 rounded-sm text-xs font-bold ${
                          idx === 0 ? 'bg-amber-500 text-slate-950' :
                          idx === 1 ? 'bg-slate-300 text-slate-950' :
                          idx === 2 ? 'bg-amber-700 text-white' :
                          'text-slate-400 bg-slate-800'
                        }`}>
                          {idx + 1}
                        </span>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-medium text-white">{poi.poi_name || poi.name || poi.poi_id}</div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          Mã: <span className="font-mono text-slate-400">{poi.poi_id}</span>
                          {poi.category && (
                            <span className="ml-2 px-1 py-0.2 rounded-sm bg-slate-800 text-slate-300 text-[10px]">
                              {poi.category}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center font-medium text-indigo-400">
                        {started.toLocaleString('vi-VN')} lượt
                      </td>
                      <td className="py-2.5 px-3 text-center text-emerald-400 font-medium">
                        {completed.toLocaleString('vi-VN')} lượt
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className="w-16 h-1.5 rounded-sm bg-slate-800 overflow-hidden">
                            <div 
                              className="h-full bg-emerald-500 rounded-sm"
                              style={{ width: `${Math.min(100, Math.max(0, compRate))}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-slate-200">{compRate}%</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center text-slate-400">
                        {poi.avg_listen_duration_seconds ? `${poi.avg_listen_duration_seconds}s` : '--'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <span className="px-2 py-0.5 rounded-sm bg-blue-950 text-blue-300 text-xs border border-blue-900">
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
          <div className="text-center py-8 text-slate-400 text-sm">
            Chưa có đủ dữ liệu sự kiện phát để xếp hạng POI.
          </div>
        )}
      </div>

      {/* Language Breakdown & Tourism Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Popular Languages */}
        <div className="bg-slate-900 border border-slate-800 rounded p-4">
          <div className="mb-3 pb-2 border-b border-slate-800">
            <h2 className="text-base font-semibold text-white">Ngôn Ngữ Thuyết Minh</h2>
            <p className="text-xs text-slate-400">Tỉ lệ lựa chọn ngôn ngữ từ du khách</p>
          </div>

          <div className="space-y-2">
            {stats?.popular_languages && stats.popular_languages.length > 0 ? (
              stats.popular_languages.map((lang: any) => {
                const totalLang = stats.popular_languages.reduce((acc: number, cur: any) => acc + cur.count, 0);
                const pct = totalLang > 0 ? Math.round((lang.count / totalLang) * 100) : 0;
                return (
                  <div key={lang.code} className="p-2.5 bg-slate-950 border border-slate-800 rounded flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{getLanguageName(lang.code)}</span>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <div className="w-20 h-1.5 bg-slate-800 rounded-sm overflow-hidden">
                        <div className="h-full bg-indigo-500 rounded-sm" style={{ width: `${pct}%` }}></div>
                      </div>
                      <span className="text-xs font-semibold text-white w-8 text-right">{pct}%</span>
                      <span className="text-xs text-slate-400">({lang.count} lượt)</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-4 text-slate-400 text-xs">
                Đang sử dụng mặc định Tiếng Việt và Tiếng Anh.
              </div>
            )}
          </div>
        </div>

        {/* Tour Sessions Performance (Admin View) */}
        {user?.role !== 'poi_owner' && (
          <div className="bg-slate-900 border border-slate-800 rounded p-4">
            <div className="mb-3 pb-2 border-b border-slate-800">
              <h2 className="text-base font-semibold text-white">Thống Kê Tuyến Đi Bộ</h2>
              <p className="text-xs text-slate-400">Hiệu suất và tỷ lệ hoàn thành hành trình tham quan</p>
            </div>

            {tourStats.length > 0 ? (
              <div className="space-y-2">
                {tourStats.slice(0, 4).map((tour: any) => (
                  <div key={tour.tour_id} className="p-2.5 bg-slate-950 border border-slate-800 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h4 className="font-medium text-white text-sm line-clamp-1">{tour.title || tour.tour_id}</h4>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {tour.total_sessions || 0} bắt đầu • {tour.completed_sessions || 0} hoàn tất
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-sm bg-emerald-950 text-emerald-300 text-xs border border-emerald-900">
                        {tour.completion_rate_percent ?? 0}% hoàn thành
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-400 text-xs">
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
