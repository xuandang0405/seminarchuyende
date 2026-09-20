import React, { useEffect, useState } from 'react';
import { 
  QrCode, 
  Plus, 
  Ban, 
  Eye, 
  Printer, 
  RotateCw, 
  ExternalLink, 
  Trash2,
  Route,
  MapPin
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useAuth } from '../context/AuthContext';
import { qrService, QRCodeItem } from '../services/qrService';
import { poiService, POI } from '../services/poiService';
import { tourService, Tour } from '../services/tourService';
import { Badge, Button, PageHeader, EmptyState } from '../components/ui';

export const QRCodes: React.FC = () => {
  const { user } = useAuth();
  const [pois, setPois] = useState<POI[]>([]);
  const [tours, setTours] = useState<Tour[]>([]);
  const [qrs, setQrs] = useState<QRCodeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [previewQr, setPreviewQr] = useState<QRCodeItem | null>(null);
  const [printQr, setPrintQr] = useState<QRCodeItem | null>(null);
  const [deleteConfirmQr, setDeleteConfirmQr] = useState<QRCodeItem | null>(null);

  // Form state
  const [targetType, setTargetType] = useState<'tour' | 'poi'>('tour');
  const [selectedTourId, setSelectedTourId] = useState('');
  const [selectedPoiId, setSelectedPoiId] = useState('');
  const [code, setCode] = useState('');
  const [locationDesc, setLocationDesc] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchQRs = async () => {
    try {
      const data = await qrService.getQRCodes();
      if (Array.isArray(data)) {
        setQrs(data);
        return;
      }
    } catch (err) {
      console.warn('Could not fetch live QRs', err);
      setQrs([]);
    }
  };

  const fetchData = async () => {
    try {
      const [poisRes, toursRes] = await Promise.all([
        poiService.getPOIs({ limit: 100 }),
        tourService.getTours(),
      ]);
      const pItems = poisRes.items || [];
      setPois(pItems);
      if (pItems.length > 0 && !selectedPoiId) {
        setSelectedPoiId(pItems[0].id);
      }

      setTours(toursRes || []);
      if (toursRes && toursRes.length > 0 && !selectedTourId) {
        setSelectedTourId(toursRes[0].id || (toursRes[0] as any)._id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    Promise.all([fetchData(), fetchQRs()]).finally(() => setLoading(false));
  }, []);

  const getQrTargetUrl = (qr: QRCodeItem) => {
    const isTour = qr.target_type === 'tour' || !!qr.tour_id;
    const targetId = isTour ? (qr.tour_id || qr.poi_id) : qr.poi_id;
    const typeParam = isTour ? 'tour' : 'poi';
    return `${window.location.origin}/client/?type=${typeParam}&id=${encodeURIComponent(targetId || '')}&qr=${encodeURIComponent(qr.code)}`;
  };

  const handleCreateQR = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('create');
    setMessage(null);
    try {
      const isTour = targetType === 'tour';
      const created = await qrService.createQRCode({
        target_type: targetType,
        tour_id: isTour ? selectedTourId : undefined,
        poi_id: isTour ? undefined : selectedPoiId,
        code: code.trim(),
        location_description: locationDesc.trim() || (isTour ? 'Tờ rơi / Poster Tuyến Tour' : 'Bảng thông tin du lịch'),
      });

      let targetName = 'Điểm đến';
      if (isTour) {
        const tObj = tours.find((t) => (t.id || (t as any)._id) === selectedTourId);
        targetName = tObj ? tObj.name : selectedTourId;
      } else {
        const poiObj = pois.find((p) => p.id === selectedPoiId);
        targetName = poiObj ? poiObj.name : selectedPoiId;
      }

      const newQr: QRCodeItem = {
        id: created.id || (created as any)._id,
        code: created.code || code,
        target_type: targetType,
        tour_id: isTour ? selectedTourId : undefined,
        poi_id: isTour ? undefined : selectedPoiId,
        target_name: targetName,
        poi_name: isTour ? `Tour: ${targetName}` : targetName,
        location_description: locationDesc || (isTour ? 'Tờ rơi / Poster Tuyến Tour' : 'Bảng thông tin du lịch'),
        is_active: true,
      };

      setQrs([newQr, ...qrs]);
      setMessage({ type: 'success', text: `Tạo mã QR "${code}" cho ${isTour ? 'Tuyến Tour' : 'Địa Điểm'} thành công!` });
      setShowCreateModal(false);
      setCode('');
      setLocationDesc('');
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Tạo mã QR thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleActivate = async (qrId: string) => {
    setActionLoading(`act_${qrId}`);
    setMessage(null);
    try {
      await qrService.activateQRCode(qrId);
      setQrs(qrs.map((q) => q.id === qrId ? { ...q, is_active: true } : q));
      setMessage({ type: 'success', text: 'Đã kích hoạt lại mã QR thành công!' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Kích hoạt lại thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeactivate = async (qrId: string) => {
    setActionLoading(`deact_${qrId}`);
    setMessage(null);
    try {
      await qrService.deactivateQRCode(qrId);
      setQrs(qrs.map((q) => q.id === qrId ? { ...q, is_active: false } : q));
      setMessage({ type: 'success', text: 'Đã vô hiệu hóa mã QR.' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Vô hiệu hóa thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmQr) return;
    setActionLoading(`del_${deleteConfirmQr.id}`);
    setMessage(null);
    try {
      await qrService.deleteQRCode(deleteConfirmQr.id);
      setQrs(qrs.filter((q) => q.id !== deleteConfirmQr.id));
      setMessage({ type: 'success', text: `Đã xóa mã QR "${deleteConfirmQr.code}" thành công.` });
      setDeleteConfirmQr(null);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Xóa mã QR thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const handlePrint = (qr: QRCodeItem) => {
    setPrintQr(qr);
    setTimeout(() => {
      window.print();
    }, 300);
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Unified Page Header */}
      <PageHeader
        title="Quản Lý Mã QR Điểm Đến & Tuyến Tour"
        description="Gắn mã QR tại các bảng chỉ dẫn, standee di tích hoặc tờ rơi để du khách quét mở Tour hoặc nghe thuyết minh ngay"
        actions={
          (user?.role === 'admin' || user?.role === 'super_admin') ? (
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                setShowCreateModal(true);
                setCode(`QR_${targetType === 'tour' ? 'TOUR' : 'POI'}_${Date.now().toString().slice(-4)}`);
              }}
            >
              + Tạo Mã QR Mới
            </Button>
          ) : undefined
        }
      />

      {message && (
        <div
          className={`p-4 rounded-xl text-sm font-medium flex items-center space-x-2.5 ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
              : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${message.type === 'success' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
          <span>{message.text}</span>
        </div>
      )}

      {/* QR Codes Grid */}
      {loading ? (
        <div className="text-center py-20 text-slate-400 font-medium">Đang tải danh sách mã QR...</div>
      ) : qrs.length === 0 ? (
        <EmptyState
          title="Chưa có mã QR nào được tạo"
          description="Hãy tạo mã QR đầu tiên cho Tuyến Tour hoặc Địa Điểm để in standee/tờ rơi quảng bá Quận 4."
          action={
            (user?.role === 'admin' || user?.role === 'super_admin') ? (
              <Button variant="primary" size="sm" onClick={() => setShowCreateModal(true)}>
                Tạo mã QR đầu tiên
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {qrs.map((qr) => {
            const isTour = qr.target_type === 'tour' || !!qr.tour_id;
            const targetUrl = getQrTargetUrl(qr);
            const displayName = qr.target_name || qr.poi_name || (isTour ? 'Tuyến Tour Quận 4' : 'Địa điểm POI');

            return (
              <div 
                key={qr.id} 
                className={`bg-slate-900 border rounded-2xl p-6 flex flex-col justify-between transition-all ${
                  qr.is_active ? 'border-slate-800 hover:border-slate-700 shadow-sm' : 'border-rose-900/30 bg-slate-950/60 opacity-80'
                }`}
              >
                <div>
                  {/* Top Status & Target Badge */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded-lg">
                        {qr.code}
                      </span>
                      <Badge variant={isTour ? 'purple' : 'info'} size="sm" showDot>
                        {isTour ? 'Tuyến Tour' : 'Điểm Đến'}
                      </Badge>
                    </div>

                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                      qr.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {qr.is_active ? 'Đang hiệu lực' : 'Đã vô hiệu'}
                    </span>
                  </div>

                  {/* QR Image & Target info */}
                  <div className="flex items-start space-x-4 mb-4">
                    <div 
                      onClick={() => setPreviewQr(qr)}
                      className="p-2 bg-white rounded-xl shadow cursor-pointer hover:scale-105 transition-transform shrink-0 border border-slate-200"
                      title="Bấm để xem phóng to mã QR"
                    >
                      <QRCodeSVG 
                        value={targetUrl} 
                        size={80} 
                        level="M" 
                        includeMargin={false} 
                      />
                    </div>

                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-bold text-white line-clamp-2 leading-snug">{displayName}</h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-1">{qr.location_description || (isTour ? 'Tờ rơi / Poster Tuyến Tour' : 'Bảng thông tin du lịch')}</p>
                      <p className="text-[11px] text-slate-500 font-mono mt-1 truncate">
                        {isTour ? `TOUR: ${qr.tour_id || qr.poi_id}` : `POI: ${qr.poi_id}`}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => setPreviewQr(qr)}
                      className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium transition-colors flex items-center space-x-1 border border-slate-700/60"
                      title="Xem chi tiết mã QR"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Xem</span>
                    </button>

                    <button
                      onClick={() => handlePrint(qr)}
                      className="px-2.5 py-1.5 rounded-xl bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-300 text-xs font-medium transition-colors flex items-center space-x-1 border border-indigo-500/25"
                      title="In poster / standee mã QR"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      <span>In QR</span>
                    </button>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    {qr.is_active ? (
                      <button
                        onClick={() => handleDeactivate(qr.id)}
                        disabled={actionLoading === `deact_${qr.id}`}
                        className="px-2.5 py-1.5 rounded-xl bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-xs font-medium transition-colors border border-amber-500/20 disabled:opacity-50"
                        title="Vô hiệu hóa mã QR"
                      >
                        Khóa
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivate(qr.id)}
                        disabled={actionLoading === `act_${qr.id}`}
                        className="px-2.5 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 text-xs font-medium transition-colors border border-emerald-500/20 disabled:opacity-50"
                        title="Kích hoạt lại mã QR"
                      >
                        Mở
                      </button>
                    )}

                    {(user?.role === 'admin' || user?.role === 'super_admin') && (
                      <button
                        onClick={() => setDeleteConfirmQr(qr)}
                        className="p-1.5 rounded-xl bg-rose-500/10 text-rose-400 hover:bg-rose-500/25 border border-rose-500/20 transition-colors"
                        title="Xóa mã QR vĩnh viễn"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: View QR Code Detail */}
      {previewQr && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl text-center animate-in zoom-in-95 duration-200">
            <div className="mb-2">
              <Badge variant={previewQr.target_type === 'tour' || previewQr.tour_id ? 'purple' : 'info'} size="sm" showDot>
                {previewQr.target_type === 'tour' || previewQr.tour_id ? 'Mã QR Tuyến Tour' : 'Mã QR Điểm Đến'}
              </Badge>
            </div>
            <h2 className="text-base font-bold text-white mb-0.5">{previewQr.target_name || previewQr.poi_name}</h2>
            <p className="text-xs text-indigo-400 font-mono mb-4">{previewQr.code}</p>

            <div className="bg-white p-4 rounded-2xl inline-block shadow-inner mb-4 border border-slate-200">
              <QRCodeSVG 
                value={getQrTargetUrl(previewQr)} 
                size={210} 
                level="H" 
                includeMargin={true} 
              />
            </div>

            <p className="text-xs text-slate-400 mb-2">
              Vị trí: <span className="text-white">{previewQr.location_description || 'Bảng thông tin du lịch'}</span>
            </p>
            <div className="bg-slate-950 p-2.5 rounded-xl text-[11px] font-mono text-slate-400 break-all mb-5 text-left border border-slate-800">
              {getQrTargetUrl(previewQr)}
            </div>

            <div className="flex items-center justify-center space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPreviewQr(null)}
              >
                Đóng
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => handlePrint(previewQr)}
                icon={<Printer className="w-3.5 h-3.5" />}
              >
                In Standee
              </Button>
              <a
                href={getQrTargetUrl(previewQr)}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium flex items-center space-x-1.5 transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Mở Link</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmQr && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex items-center space-x-3 text-rose-400 mb-3">
              <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <Trash2 className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-white tracking-tight">Xác Nhận Xóa Mã QR</h2>
            </div>
            <p className="text-sm text-slate-300 mb-2">
              Bạn có chắc chắn muốn xóa mã QR <strong className="text-white font-mono">"{deleteConfirmQr.code}"</strong> ({deleteConfirmQr.target_name || deleteConfirmQr.poi_name}) không?
            </p>
            <p className="text-xs text-slate-400 mb-6 bg-slate-950 p-3 rounded-xl border border-slate-800">
              ⚠️ Du khách sẽ không thể quét mã này để mở hành trình hoặc nghe thuyết minh nữa.
            </p>
            <div className="flex justify-end space-x-2.5">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeleteConfirmQr(null)}
              >
                Hủy Bỏ
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={handleDeleteConfirm}
                loading={actionLoading === `del_${deleteConfirmQr.id}`}
              >
                Xác Nhận Xóa
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Printable Badge Frame */}
      {printQr && (
        <div className="hidden print:block fixed inset-0 bg-white text-black p-8 z-[9999]">
          <div className="max-w-md mx-auto border-4 border-black p-8 rounded-2xl text-center space-y-4">
            <div className="text-xs uppercase tracking-widest font-extrabold text-slate-700">
              Hệ Thống Thuyết Minh Du Lịch Tự Động Quận 4
            </div>
            <div className="inline-block px-3 py-1 rounded-full text-xs font-bold border border-black uppercase">
              {printQr.target_type === 'tour' || printQr.tour_id ? 'Mã QR Tuyến Tour Khám Phá' : 'Mã QR Điểm Đến Thuyết Minh'}
            </div>
            <h1 className="text-2xl font-black text-black">{printQr.target_name || printQr.poi_name}</h1>
            <div className="py-2 flex justify-center">
              <QRCodeSVG 
                value={getQrTargetUrl(printQr)} 
                size={260} 
                level="H" 
                includeMargin={true} 
              />
            </div>
            <div className="font-mono text-sm font-bold bg-slate-100 py-1 px-3 rounded inline-block">
              MÃ ĐỊNH DANH: {printQr.code}
            </div>
            <p className="text-sm font-semibold text-slate-800">
              {printQr.target_type === 'tour' || printQr.tour_id
                ? '👉 Mở camera điện thoại quét mã QR để bắt đầu hành trình tham quan và nghe thuyết minh tự động từng chặng!'
                : '👉 Mở camera điện thoại quét mã QR để nghe thuyết minh tự động và khám phá lịch sử, ẩm thực tại điểm đến!'}
            </p>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200">
            <h2 className="text-xl font-bold text-white mb-1 tracking-tight">Tạo Mã QR Mới</h2>
            <p className="text-xs text-slate-400 mb-4">Chọn tạo mã cho Tuyến Tour hoặc Địa Điểm đơn lẻ</p>

            <form onSubmit={handleCreateQR} className="space-y-4">
              {/* Type Switcher */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1.5">Loại Đối Tượng</label>
                <div className="grid grid-cols-2 gap-2 p-1 bg-slate-950 border border-slate-800 rounded-xl">
                  <button
                    type="button"
                    onClick={() => {
                      setTargetType('tour');
                      setCode(`QR_TOUR_${Date.now().toString().slice(-4)}`);
                    }}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 ${
                      targetType === 'tour'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Route className="w-3.5 h-3.5" />
                    <span>Tuyến Tour</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setTargetType('poi');
                      setCode(`QR_POI_${Date.now().toString().slice(-4)}`);
                    }}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold transition-all flex items-center justify-center space-x-1.5 ${
                      targetType === 'poi'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    <span>Địa Điểm (POI)</span>
                  </button>
                </div>
              </div>

              {/* Target Selector */}
              {targetType === 'tour' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Chọn Tuyến Tour</label>
                  <select
                    value={selectedTourId}
                    onChange={(e) => setSelectedTourId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {tours.map((t) => (
                      <option key={t.id || (t as any)._id} value={t.id || (t as any)._id}>
                        {t.name} ({t.poi_ids?.length || 0} điểm dừng)
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Chọn Địa Điểm POI</label>
                  <select
                    value={selectedPoiId}
                    onChange={(e) => setSelectedPoiId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {pois.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mã QR Định Danh (Code)</label>
                <input
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Ví dụ: QR_TOUR_01 hoặc QR_BNR_01"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm font-mono focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">Mã định danh duy nhất để du khách quét hoặc in trên standee/poster</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mô Tả Vị Trí Dán Thẻ</label>
                <input
                  type="text"
                  value={locationDesc}
                  onChange={(e) => setLocationDesc(e.target.value)}
                  placeholder={targetType === 'tour' ? 'Ví dụ: Tờ rơi quảng bá, vé tham quan, bến tàu...' : 'Ví dụ: Cổng di tích Bến Nhà Rồng, Bàn số 5 Quán Ốc Oanh...'}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end space-x-2.5 pt-4 border-t border-slate-800">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setShowCreateModal(false)}
                >
                  Hủy Bỏ
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  loading={actionLoading === 'create'}
                >
                  Tạo Mã QR
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
