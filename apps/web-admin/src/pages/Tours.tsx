import React, { useState, useEffect } from 'react';
import { 
  Route, 
  MapPin, 
  Plus, 
  CheckCircle2, 
  AlertCircle, 
  Edit3, 
  Trash2, 
  ArrowUp, 
  ArrowDown, 
  X, 
  DollarSign, 
  SlidersHorizontal,
  QrCode,
  ExternalLink,
  Printer
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useAuth } from '../context/AuthContext';
import { tourService, Tour } from '../services/tourService';
import { poiService, POI } from '../services/poiService';
import { Badge, Button, Modal, PageHeader, EmptyState } from '../components/ui';

export const Tours: React.FC = () => {
  const { user } = useAuth();
  const [tours, setTours] = useState<Tour[]>([]);
  const [availablePois, setAvailablePois] = useState<POI[]>([]);
  const [selectedTour, setSelectedTour] = useState<Tour | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [qrTourModal, setQrTourModal] = useState<Tour | null>(null);

  // Pricing Form State
  const [isPaid, setIsPaid] = useState(false);
  const [priceVnd, setPriceVnd] = useState(150000);
  const [forSale, setForSale] = useState(true);

  // Tour Form State (Create & Edit)
  const [tourName, setTourName] = useState('');
  const [tourDescription, setTourDescription] = useState('');
  const [selectedPoiIds, setSelectedPoiIds] = useState<string[]>([]);
  const [createIsPaid, setCreateIsPaid] = useState(false);
  const [createPriceVnd, setCreatePriceVnd] = useState(100000);

  const fetchTours = async () => {
    setLoading(true);
    try {
      const data = await tourService.getTours();
      setTours(data);
      if (data.length > 0) {
        fetchTourDetail(data[0].id || (data[0] as any)._id);
      } else {
        setSelectedTour(null);
      }
    } catch (err: any) {
      console.error(err);
      setMessage({ type: 'error', text: err.message || 'Không thể tải danh sách tour.' });
    } finally {
      setLoading(false);
    }
  };

  const fetchTourDetail = async (tourId: string) => {
    try {
      const data = await tourService.getTourDetail(tourId);
      setSelectedTour(data);
      setIsPaid(data.is_paid || false);
      setPriceVnd(data.price_vnd || data.price_amount || 0);
      setForSale(data.for_sale !== false);
    } catch (err: any) {
      console.error(err);
    }
  };

  const fetchPOIs = async () => {
    try {
      const res = await poiService.getPOIs({ limit: 100 });
      setAvailablePois(res.items || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchTours();
    fetchPOIs();
  }, []);

  // Format currency
  const formatVND = (val: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);
  };

  // Open Create Modal
  const handleOpenCreateModal = () => {
    setTourName('');
    setTourDescription('');
    setSelectedPoiIds([]);
    setCreateIsPaid(false);
    setCreatePriceVnd(100000);
    setShowCreateModal(true);
  };

  // Open Edit Modal
  const handleOpenEditModal = () => {
    if (!selectedTour) return;
    setTourName(selectedTour.name || selectedTour.title || '');
    setTourDescription(selectedTour.description || '');
    const currentPois = selectedTour.poi_ids || selectedTour.pois?.map((p: any) => p.id || p._id) || [];
    setSelectedPoiIds([...currentPois]);
    setShowEditModal(true);
  };

  // Reorder Stops in Tour Form
  const movePoiStop = (index: number, direction: 'up' | 'down') => {
    const newOrder = [...selectedPoiIds];
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= newOrder.length) return;
    const temp = newOrder[index];
    newOrder[index] = newOrder[targetIdx];
    newOrder[targetIdx] = temp;
    setSelectedPoiIds(newOrder);
  };

  const togglePoiSelection = (poiId: string) => {
    if (selectedPoiIds.includes(poiId)) {
      setSelectedPoiIds(selectedPoiIds.filter((id) => id !== poiId));
    } else {
      setSelectedPoiIds([...selectedPoiIds, poiId]);
    }
  };

  // Submit Create Tour
  const handleCreateTourSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedPoiIds.length === 0) {
      alert('Vui lòng chọn ít nhất một điểm dừng cho tuyến tour.');
      return;
    }

    setActionLoading(true);
    setMessage(null);
    try {
      const price = createIsPaid ? Math.max(0, parseInt(String(createPriceVnd), 10) || 0) : 0;
      const created = await tourService.createTour({
        name: tourName.trim(),
        description: tourDescription.trim(),
        poi_ids: selectedPoiIds,
        price_amount: price,
        price_vnd: price,
        currency: 'VND',
        is_paid: createIsPaid,
        is_purchasable: true,
        is_active: true
      });

      setMessage({ type: 'success', text: `Đã tạo tuyến tour "${tourName}" thành công!` });
      setShowCreateModal(false);
      await fetchTours();
      if (created?.id || (created as any)?._id) {
        fetchTourDetail(created.id || (created as any)._id);
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Tạo tour thất bại.' });
    } finally {
      setActionLoading(false);
    }
  };

  // Submit Edit Tour
  const handleEditTourSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTour) return;
    if (selectedPoiIds.length === 0) {
      alert('Vui lòng chọn ít nhất một điểm dừng cho tuyến tour.');
      return;
    }

    setActionLoading(true);
    setMessage(null);
    try {
      await tourService.updateTour(selectedTour.id, {
        name: tourName.trim(),
        description: tourDescription.trim(),
        poi_ids: selectedPoiIds
      });

      setMessage({ type: 'success', text: `Cập nhật thông tin tour "${tourName}" thành công!` });
      setShowEditModal(false);
      fetchTourDetail(selectedTour.id);
      fetchTours();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Cập nhật tour thất bại.' });
    } finally {
      setActionLoading(false);
    }
  };

  // Submit Update Pricing
  const handleUpdatePricing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTour) return;
    setActionLoading(true);
    setMessage(null);

    try {
      const numericPrice = isPaid ? Math.max(0, parseInt(String(priceVnd), 10) || 0) : 0;
      await tourService.updateTourPricing(selectedTour.id, {
        price_amount: numericPrice,
        price_vnd: numericPrice,
        currency: 'VND',
        is_purchasable: forSale,
        for_sale: forSale,
        is_paid: isPaid,
        preview_enabled: true
      });

      setMessage({ type: 'success', text: `Đã cập nhật chính sách giá cho tour "${selectedTour.name}" thành công!` });
      setShowPricingModal(false);
      fetchTourDetail(selectedTour.id);
      fetchTours();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Cập nhật giá vé thất bại.' });
    } finally {
      setActionLoading(false);
    }
  };

  // Confirm Delete Tour
  const handleConfirmDeleteTour = async () => {
    if (!selectedTour) return;
    setActionLoading(true);
    setMessage(null);

    try {
      await tourService.deleteTour(selectedTour.id);
      setMessage({ type: 'success', text: `Đã xóa tuyến tour "${selectedTour.name}" thành công.` });
      setShowDeleteModal(false);
      fetchTours();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Xóa tour thất bại.' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Unified Page Header */}
      <PageHeader
        title="Quản Lý Tuyến Du Lịch"
        description="Thiết lập lộ trình điểm dừng có thứ tự, nội dung thuyết minh tự động và chính sách bán vé tham quan"
        actions={
          (user?.role === 'admin' || user?.role === 'super_admin') ? (
            <Button
              variant="primary"
              size="md"
              onClick={handleOpenCreateModal}
            >
              + Thêm Tour Mới
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

      {loading ? (
        <div className="text-center py-16 text-slate-400">Đang tải danh sách tour...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Tours List */}
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Danh Sách Tuyến Tour ({tours.length})
            </h2>
            {tours.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800">
                Chưa có tour nào. Hãy bấm "Thêm Tour Mới" để tạo lộ trình đầu tiên.
              </div>
            ) : (
              tours.map((t: any) => {
                const tourId = t.id || t._id;
                const isSelected = selectedTour?.id === tourId || (selectedTour as any)?._id === tourId;
                const isTourPaid = t.is_paid || (t.price_amount && t.price_amount > 0);
                return (
                  <div
                    key={tourId}
                    onClick={() => fetchTourDetail(tourId)}
                    className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-slate-900 border-indigo-500/80 shadow-lg shadow-indigo-500/10'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 text-indigo-400">
                        <Route className="w-4 h-4" />
                        <span className="text-xs font-semibold">{t.poi_count || t.poi_ids?.length || 0} điểm dừng</span>
                      </div>
                      {isTourPaid ? (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-bold border border-amber-500/20">
                          {formatVND(t.price_vnd || t.price_amount || 0)}
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">
                          Miễn Phí
                        </span>
                      )}
                    </div>
                    <h3 className="font-bold text-white text-base">{t.name || t.title}</h3>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{t.description || 'Chưa có mô tả chi tiết'}</p>
                  </div>
                );
              })
            )}
          </div>

          {/* Tour Details & Ordered Stops */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between">
            {selectedTour ? (
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 uppercase">
                      Chi Tiết Tuyến Tour
                    </span>
                    <h2 className="text-xl font-bold text-white mt-2">{selectedTour.name || selectedTour.title}</h2>
                    <p className="text-sm text-slate-400 mt-1">{selectedTour.description || 'Chưa có mô tả'}</p>

                    <div className="flex flex-wrap items-center gap-2 mt-4">
                      <button
                        onClick={() => setQrTourModal(selectedTour)}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 text-xs font-medium transition-all"
                        title="Tạo mã QR & quét mở tuyến tour này"
                      >
                        <QrCode className="w-3.5 h-3.5" />
                        <span>Mã QR Tuyến Tour</span>
                      </button>

                      {(user?.role === 'admin' || user?.role === 'super_admin') && (
                        <>
                          <button
                            onClick={handleOpenEditModal}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-all"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                            <span>Chỉnh Sửa Lộ Trình</span>
                          </button>
                          <button
                            onClick={() => setShowDeleteModal(true)}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/25 text-red-400 border border-red-500/20 text-xs font-medium transition-all"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>Xóa Tuyến Tour</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Pricing Info Card */}
                  <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 shrink-0 min-w-[220px]">
                    <div className="text-xs text-slate-400 uppercase font-semibold">Chính Sách Vé</div>
                    <div className="text-lg font-bold text-white mt-1">
                      {selectedTour.is_paid || (selectedTour.price_amount && selectedTour.price_amount > 0)
                        ? formatVND(selectedTour.price_vnd || selectedTour.price_amount || 0)
                        : 'Miễn Phí'}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      {selectedTour.for_sale !== false ? '🟢 Đang mở bán vé' : '⚪ Tạm dừng bán vé'}
                    </div>

                    {(user?.role === 'admin' || user?.role === 'super_admin') && (
                      <button
                        onClick={() => setShowPricingModal(true)}
                        className="mt-3 w-full inline-flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold transition-all"
                      >
                        <SlidersHorizontal className="w-3.5 h-3.5" />
                        <span>Cài Đặt Giá Vé</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Ordered Stops List */}
                <div className="border-t border-slate-800 pt-4">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">
                    Thứ Tự Các Điểm Dừng ({selectedTour.pois?.length || 0} điểm)
                  </h3>

                  {(!selectedTour.pois || selectedTour.pois.length === 0) ? (
                    <div className="p-6 text-center text-slate-500 bg-slate-950 rounded-xl border border-slate-800">
                      Tuyến tour này chưa có điểm dừng nào. Bấm "Chỉnh Sửa Lộ Trình" để thêm điểm dừng.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {selectedTour.pois.map((p: any, index: number) => (
                        <div
                          key={p.id || p._id || index}
                          className="flex items-center space-x-4 p-4 rounded-xl bg-slate-950 border border-slate-800"
                        >
                          <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-400 font-bold flex items-center justify-center shrink-0 border border-indigo-500/30">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-bold text-white text-sm truncate">{p.name}</h4>
                            <p className="text-xs text-slate-400 truncate">{p.address || 'Quận 4, TP.HCM'}</p>
                          </div>
                          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300 capitalize">
                            {p.category || 'Điểm tham quan'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-slate-500">
                Chọn một tuyến tour ở cột bên trái để xem chi tiết hoặc tạo mới.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Tour Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-white">Thêm Tuyến Tour Mới</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Tạo lộ trình có thứ tự điểm dừng và thiết lập chính sách bán vé
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateTourSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Tên Tuyến Tour</label>
                <input
                  type="text"
                  required
                  value={tourName}
                  onChange={(e) => setTourName(e.target.value)}
                  placeholder="Ví dụ: Hành Trình Lịch Sử Quận 4 & Cầu Mống"
                  className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mô Tả Lộ Trình</label>
                <textarea
                  rows={2}
                  value={tourDescription}
                  onChange={(e) => setTourDescription(e.target.value)}
                  placeholder="Giới thiệu về lộ trình tham quan, thời lượng dự kiến..."
                  className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Stop Selector & Ordering */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300 uppercase">
                  Chọn & Sắp Xếp Thứ Tự Điểm Dừng ({selectedPoiIds.length} đã chọn)
                </label>

                {/* Selected Stops Ordered List */}
                {selectedPoiIds.length > 0 && (
                  <div className="space-y-2 p-3 bg-slate-950 rounded-xl border border-slate-800">
                    <span className="text-[11px] font-semibold text-indigo-400 uppercase">Lộ trình đã chọn:</span>
                    {selectedPoiIds.map((pid, idx) => {
                      const poi = availablePois.find((p: any) => (p.id || p._id) === pid);
                      return (
                        <div key={pid} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                          <div className="flex items-center space-x-2 min-w-0">
                            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px]">
                              {idx + 1}
                            </span>
                            <span className="text-white font-medium truncate">{poi?.name || pid}</span>
                          </div>
                          <div className="flex items-center space-x-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => movePoiStop(idx, 'up')}
                              disabled={idx === 0}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
                            >
                              <ArrowUp className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => movePoiStop(idx, 'down')}
                              disabled={idx === selectedPoiIds.length - 1}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
                            >
                              <ArrowDown className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => togglePoiSelection(pid)}
                              className="p-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* All POIs Picker */}
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 max-h-48 overflow-y-auto space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                    Bấm vào điểm để thêm vào lộ trình:
                  </span>
                  {availablePois.map((poi: any) => {
                    const pid = poi.id || poi._id;
                    const isChecked = selectedPoiIds.includes(pid);
                    return (
                      <div
                        key={pid}
                        onClick={() => togglePoiSelection(pid)}
                        className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all ${
                          isChecked ? 'bg-indigo-600/20 border border-indigo-500/40 text-white' : 'hover:bg-slate-900 text-slate-300'
                        }`}
                      >
                        <span className="text-xs font-medium truncate">{poi.name}</span>
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {poi.category}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Pricing Settings */}
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">Thu Phí Tham Quan (Tour Có Trả Phí)</span>
                  <input
                    type="checkbox"
                    checked={createIsPaid}
                    onChange={(e) => setCreateIsPaid(e.target.checked)}
                    className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                  />
                </div>

                {createIsPaid && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                      Giá Vé (VND / lượt người)
                    </label>
                    <input
                      type="number"
                      min="10000"
                      step="5000"
                      required
                      value={createPriceVnd}
                      onChange={(e) => setCreatePriceVnd(Number(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono text-sm"
                    />
                    <p className="text-[11px] text-slate-400 mt-1">Định dạng: {formatVND(createPriceVnd)}</p>
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 disabled:opacity-50"
                >
                  {actionLoading ? 'Đang tạo...' : 'Tạo Tuyến Tour'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Tour Modal */}
      {showEditModal && selectedTour && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-2xl shadow-2xl max-h-[92vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Chỉnh Sửa Lộ Trình Tour</h2>
              <button
                type="button"
                onClick={() => setShowEditModal(false)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleEditTourSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Tên Tuyến Tour</label>
                <input
                  type="text"
                  required
                  value={tourName}
                  onChange={(e) => setTourName(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Mô Tả</label>
                <textarea
                  rows={2}
                  value={tourDescription}
                  onChange={(e) => setTourDescription(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Stops Ordering */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300 uppercase">
                  Thứ Tự Điểm Dừng ({selectedPoiIds.length} điểm)
                </label>

                {selectedPoiIds.length > 0 && (
                  <div className="space-y-2 p-3 bg-slate-950 rounded-xl border border-slate-800">
                    {selectedPoiIds.map((pid, idx) => {
                      const poi = availablePois.find((p: any) => (p.id || p._id) === pid);
                      return (
                        <div key={pid} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                          <div className="flex items-center space-x-2 min-w-0">
                            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-[10px]">
                              {idx + 1}
                            </span>
                            <span className="text-white font-medium truncate">{poi?.name || pid}</span>
                          </div>
                          <div className="flex items-center space-x-1 shrink-0">
                            <button
                              type="button"
                              onClick={() => movePoiStop(idx, 'up')}
                              disabled={idx === 0}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
                            >
                              <ArrowUp className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => movePoiStop(idx, 'down')}
                              disabled={idx === selectedPoiIds.length - 1}
                              className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30"
                            >
                              <ArrowDown className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => togglePoiSelection(pid)}
                              className="p-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Available POIs */}
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 max-h-48 overflow-y-auto space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase block mb-1">
                    Thêm điểm dừng khác:
                  </span>
                  {availablePois.map((poi: any) => {
                    const pid = poi.id || poi._id;
                    const isChecked = selectedPoiIds.includes(pid);
                    return (
                      <div
                        key={pid}
                        onClick={() => togglePoiSelection(pid)}
                        className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all ${
                          isChecked ? 'bg-indigo-600/20 border border-indigo-500/40 text-white' : 'hover:bg-slate-900 text-slate-300'
                        }`}
                      >
                        <span className="text-xs font-medium truncate">{poi.name}</span>
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {poi.category}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 disabled:opacity-50"
                >
                  {actionLoading ? 'Đang lưu...' : 'Lưu Thay Đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Pricing Policy Modal */}
      {showPricingModal && selectedTour && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-2">Chính Sách Bán Vé Tour</h2>
            <p className="text-xs text-slate-400 mb-6">
              Thiết lập phí tham quan hoặc cung cấp tour miễn phí cho du khách
            </p>

            <form onSubmit={handleUpdatePricing} className="space-y-4">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-sm font-semibold text-white">Thu Phí Tham Quan (Tour Có Thu Phí)</span>
                <input
                  type="checkbox"
                  checked={isPaid}
                  onChange={(e) => setIsPaid(e.target.checked)}
                  className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                />
              </div>

              {isPaid && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    Giá Vé (VND / lượt người)
                  </label>
                  <input
                    type="number"
                    min="10000"
                    step="5000"
                    required
                    value={priceVnd}
                    onChange={(e) => setPriceVnd(Number(e.target.value))}
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white font-mono text-sm"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Định dạng: {formatVND(priceVnd)}</p>
                </div>
              )}

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800">
                <span className="text-sm font-semibold text-white">Mở Bán Vé Cho Du Khách</span>
                <input
                  type="checkbox"
                  checked={forSale}
                  onChange={(e) => setForSale(e.target.checked)}
                  className="w-5 h-5 accent-indigo-600 rounded cursor-pointer"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowPricingModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30"
                >
                  {actionLoading ? 'Đang lưu...' : 'Lưu Thay Đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Tour Confirmation Modal */}
      {showDeleteModal && selectedTour && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center space-x-3 text-red-400 mb-3">
              <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20">
                <Trash2 className="w-6 h-6" />
              </div>
              <h2 className="text-lg font-bold text-white">Xác Nhận Xóa Tour</h2>
            </div>
            
            <p className="text-sm text-slate-300 mb-2">
              Bạn có chắc chắn muốn xóa tuyến tour <strong className="text-white">"{selectedTour.name}"</strong> không?
            </p>
            <p className="text-xs text-slate-400 mb-6 bg-slate-950 p-3 rounded-xl border border-slate-800">
              ⚠️ Tuyến tour này sẽ bị xóa mềm và ẩn khỏi giao diện du khách. Dữ liệu các địa điểm dừng vẫn được giữ nguyên vẹn.
            </p>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition-all"
              >
                Hủy Bỏ
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteTour}
                disabled={actionLoading}
                className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-semibold shadow-lg shadow-red-600/30 transition-all disabled:opacity-50"
              >
                {actionLoading ? 'Đang xóa...' : 'Xác Nhận Xóa'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tour QR Code Modal */}
      {qrTourModal && (
        <Modal
          isOpen={!!qrTourModal}
          onClose={() => setQrTourModal(null)}
          title={`Mã QR Tuyến Tour: ${qrTourModal.name}`}
          maxWidth="md"
        >
          <div className="flex flex-col items-center text-center space-y-4 pt-2">
            <div className="p-4 bg-white rounded-2xl shadow-xl border border-slate-200">
              <QRCodeSVG
                id="tour-qr-code-svg"
                value={`${window.location.origin}/client/?type=tour&id=${qrTourModal.id || (qrTourModal as any)._id}`}
                size={200}
                level="H"
                includeMargin={true}
              />
            </div>

            <div className="space-y-1">
              <p className="text-sm font-bold text-white">{qrTourModal.name}</p>
              <p className="text-xs text-slate-400">
                Quét mã này sẽ mở trực tiếp trang bản đồ du khách với lộ trình {qrTourModal.pois?.length || 0} điểm dừng và âm thanh thuyết minh
              </p>
              <div className="mt-2 text-[11px] text-indigo-400 font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 break-all select-all">
                {`${window.location.origin}/client/?type=tour&id=${qrTourModal.id || (qrTourModal as any)._id}`}
              </div>
            </div>

            <div className="flex items-center space-x-3 w-full pt-2">
              <a
                href={`/client/?type=tour&id=${qrTourModal.id || (qrTourModal as any)._id}`}
                target="_blank"
                rel="noreferrer"
                className="flex-1 inline-flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>Mở Thử Nghiệm</span>
              </a>
              <Button
                variant="primary"
                size="md"
                className="flex-1"
                onClick={() => {
                  window.print();
                }}
              >
                <Printer className="w-3.5 h-3.5 mr-1.5" />
                <span>In Standee</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
