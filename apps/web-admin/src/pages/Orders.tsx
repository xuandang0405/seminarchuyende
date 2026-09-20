import React, { useEffect, useState } from 'react';
import { 
  Receipt, 
  Search, 
  CheckCircle2, 
  Clock, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  CreditCard,
  QrCode,
  ArrowUpRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { orderService, OrderItem } from '../services/orderService';
import { apiClient } from '../services/apiClient';
import { Badge, Button, PageHeader, EmptyState } from '../components/ui';

export const Orders: React.FC = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const data = await orderService.getOrders(statusFilter || undefined, 0, 50);
      setOrders(Array.isArray(data) ? data : []);
    } catch (err: any) {
      console.error(err);
      setMessage({ type: 'error', text: err.message || 'Không thể nạp danh sách đơn hàng' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [statusFilter]);

  const handleReconcile = async (orderId: string) => {
    setActionLoading(`reconcile_${orderId}`);
    setMessage(null);
    try {
      const data = await orderService.reconcileOrder(orderId);
      setMessage({
        type: 'success',
        text: `Đối soát thành công đơn hàng #${orderId}. Trạng thái hiện tại: ${data?.status || 'Đã kiểm tra'}`
      });
      fetchOrders();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Đối soát thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleSimulateSuccess = async (orderId: string) => {
    setActionLoading(`simulate_${orderId}`);
    setMessage(null);
    try {
      await apiClient.post(`/payments/orders/${orderId}/simulate-success`);
      setMessage({
        type: 'success',
        text: `Đã xác nhận thanh toán thành công cho đơn hàng #${orderId} (Vé E-Ticket đã cấp)`
      });
      fetchOrders();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Giả lập thanh toán thất bại' });
    } finally {
      setActionLoading(null);
    }
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
  };

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'paid':
      case 'success':
      case 'completed':
        return <Badge variant="success" size="sm" showDot>Đã thanh toán</Badge>;
      case 'pending':
        return <Badge variant="warning" size="sm" showDot>Chờ thanh toán</Badge>;
      case 'cancelled':
      case 'failed':
        return <Badge variant="danger" size="sm" showDot>Đã hủy</Badge>;
      default:
        return <Badge variant="neutral" size="sm">{status || 'Không rõ'}</Badge>;
    }
  };

  return (
    <div className="p-4 sm:p-6 md:p-8 space-y-6 max-w-7xl mx-auto font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Unified Page Header */}
      <PageHeader
        title="Quản Lý Đơn Hàng & Vé"
        description="Theo dõi giao dịch vé tour, đơn đặt món và kích hoạt đối soát thanh toán trực tiếp"
        actions={
          <Button
            variant="secondary"
            size="md"
            onClick={fetchOrders}
            loading={loading}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />}
          >
            Làm mới
          </Button>
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

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex items-center space-x-2">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Trạng Thái:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 text-sm focus:outline-none focus:border-indigo-500 cursor-pointer transition-colors"
          >
            <option value="">Tất cả trạng thái</option>
            <option value="pending">Chờ thanh toán (Pending)</option>
            <option value="paid">Đã thanh toán (Paid)</option>
            <option value="cancelled">Đã hủy (Cancelled)</option>
          </select>
        </div>

        <div className="text-xs text-slate-400">
          Tổng cộng: <strong className="text-white font-semibold">{orders.length}</strong> đơn hàng
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl overflow-hidden shadow-lg">
        {loading ? (
          <div className="text-center py-20 text-slate-400 font-medium">Đang tải danh sách giao dịch...</div>
        ) : orders.length === 0 ? (
          <EmptyState
            title="Không có đơn hàng nào"
            description="Các đơn mua vé và dịch vụ sẽ tự động xuất hiện ở đây khi có giao dịch mới."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/70 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3.5 px-4">Mã Đơn / Thời Gian</th>
                  <th className="py-3.5 px-4">Khách Hàng</th>
                  <th className="py-3.5 px-4">Sản Phẩm / Dịch Vụ</th>
                  <th className="py-3.5 px-4">Số Tiền</th>
                  <th className="py-3.5 px-4">Trạng Thái</th>
                  <th className="py-3.5 px-4">Phương Thức</th>
                  <th className="py-3.5 px-4 text-right">Thao Tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {orders.map((order) => (
                  <tr key={order.order_id || order.id || order._id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-mono text-xs text-indigo-400 font-bold">
                        #{order.order_id || order.id || order._id}
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {order.created_at ? new Date(order.created_at).toLocaleString('vi-VN') : '--'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-white font-semibold">{order.customer_name || 'Khách Vãng Lai'}</div>
                      <div className="text-xs text-slate-400">{order.customer_email || order.customer_phone || '--'}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-white line-clamp-1">{order.item_title || order.item_id}</div>
                      <div className="text-xs text-slate-400">Số lượng: {order.quantity || 1}</div>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-emerald-400">
                      {formatVND(order.total_amount || (order.unit_price * (order.quantity || 1)))}
                    </td>
                    <td className="py-3.5 px-4">
                      {getStatusBadge(order.status)}
                    </td>
                    <td className="py-3.5 px-4 text-xs uppercase font-semibold text-slate-400">
                      {order.payment_method || 'VietQR'}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5">
                      <button
                        onClick={() => handleReconcile(order.order_id || order.id || order._id)}
                        disabled={actionLoading === `reconcile_${order.order_id || order.id || order._id}`}
                        title="Đối soát trực tiếp máy chủ thanh toán"
                        className="px-2.5 py-1 rounded-xl bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-300 text-xs font-medium border border-indigo-500/25 transition-all disabled:opacity-50"
                      >
                        {actionLoading === `reconcile_${order.order_id || order.id || order._id}` ? 'Đang kiểm tra...' : 'Đối Soát'}
                      </button>

                      {order.status === 'pending' && (
                        <button
                          onClick={() => handleSimulateSuccess(order.order_id || order.id || order._id)}
                          disabled={actionLoading === `simulate_${order.order_id || order.id || order._id}`}
                          title="Giả lập thanh toán thành công (Demo)"
                          className="px-2.5 py-1 rounded-xl bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-300 text-xs font-medium border border-emerald-500/25 transition-all disabled:opacity-50"
                        >
                          Duyệt Vé
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
