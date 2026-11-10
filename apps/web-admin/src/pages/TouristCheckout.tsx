import { newRequestId } from '../services/liveTelemetry';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { CheckCircle2, CreditCard, FlaskConical } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { ApiError, apiClient } from '../services/apiClient';
import type { UserProfile } from '../context/AuthContext';

export const formatVnd = (amount: number) => new Intl.NumberFormat('vi-VN', {
  style: 'currency', currency: 'VND',
}).format(amount);

export interface CheckoutOrder {
  order_id: string;
  status: string;
  mock_mode?: boolean;
  simulated?: boolean;
  ticket_code?: string;
  payment?: { qr_code_data?: string; checkout_url?: string };
}

export function TouristCheckout({ tourId, price, user, onPaid }: {
  tourId: string; price: number; user: UserProfile; onPaid: (order: CheckoutOrder) => void;
}) {
  const storageKey = `tourvoice_order:${user.id}:${tourId}`;
  const [order, setOrder] = useState<CheckoutOrder | null>(null);
  const latest = useRef<CheckoutOrder | null>(null);
  const [simulationEnabled, setSimulationEnabled] = useState(false);
  const [name, setName] = useState(user.full_name || '');
  const [phone, setPhone] = useState('');
  const [method, setMethod] = useState<'vietqr' | 'visa'>('vietqr');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const key = useRef(sessionStorage.getItem(storageKey + ':key') || newRequestId());
  const pendingId = order?.order_id || sessionStorage.getItem(storageKey);
  const orderPath = pendingId ? `/payments/orders/${encodeURIComponent(pendingId)}` : null;

  const record = (next: CheckoutOrder) => {
    const previous = latest.current;
    if (previous?.order_id === next.order_id && previous.status === 'paid' && next.status !== 'paid') return;
    const merged = { ...(previous?.order_id === next.order_id ? previous : null), ...next };
    latest.current = merged;
    setOrder(merged);
    sessionStorage.setItem(storageKey, next.order_id);
    if (next.status === 'paid') {
      sessionStorage.removeItem(storageKey + ':key');
      if (previous?.status !== 'paid' || previous.order_id !== next.order_id) onPaid(merged);
    }
  };
  const reset = () => {
    sessionStorage.removeItem(storageKey);
    sessionStorage.removeItem(storageKey + ':key');
    key.current = newRequestId();
    latest.current = null;
    setOrder(null);
    setMessage('');
  };
  useEffect(() => {
    const controller = new AbortController();
    apiClient.get<{ simulation_enabled: boolean }>('/payments/config', { signal: controller.signal })
      .then(config => { if (!controller.signal.aborted) setSimulationEnabled(config.simulation_enabled); }).catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!orderPath || order && !['pending', 'pending_payment'].includes(order.status)) return;
    const abort = new AbortController();
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await apiClient.get<CheckoutOrder>(orderPath, { signal: abort.signal });
        if (!abort.signal.aborted) record(next);
      } catch (error) {
        if (!abort.signal.aborted && !latest.current && error instanceof ApiError && [403, 404].includes(error.statusCode)) {
          reset();
          setMessage('Đơn đã lưu không còn khả dụng. Bạn có thể tạo đơn mới.');
          return;
        }
      }
      if (!abort.signal.aborted) timer = window.setTimeout(poll, 6000);
    };
    void poll();
    return () => { abort.abort(); window.clearInterval(timer); };
  }, [orderPath, order?.status]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true); setMessage('');
    sessionStorage.setItem(storageKey + ':key', key.current);
    try {
      const result = await apiClient.post<{ data: CheckoutOrder }>('/payments/orders', {
        item_id: tourId, customer_name: name.trim(), customer_phone: phone.trim(), payment_method: method,
      }, { headers: { 'Idempotency-Key': key.current } });
      record(result.data);
    } catch (error) { setMessage((error as Error).message); }
    finally { setBusy(false); }
  };

  const check = async (simulate = false) => {
    if (!orderPath && !simulate) return;
    setBusy(true); setMessage('');
    try {
      let next: CheckoutOrder;
      if (simulate && !simulationEnabled && orderPath) {
        next = (await apiClient.post<{ data: CheckoutOrder }>(orderPath + '/simulate-success')).data;
      } else if (simulate) {
        sessionStorage.setItem(storageKey + ':key', key.current);
        next = (await apiClient.post<{ data: CheckoutOrder }>('/payments/simulate-checkout', {
          item_id: tourId,
        }, { headers: { 'Idempotency-Key': key.current } })).data;
      } else {
        next = await apiClient.get<CheckoutOrder>(orderPath!);
      }
      record(next);
      if (next.status === 'pending_payment' || next.status === 'pending') setMessage('Đơn vẫn đang chờ xác nhận từ cổng thanh toán.');
    } catch (error) {
      if (error instanceof ApiError && error.details?.detail?.error_code === 'CHECKOUT_EXPIRED') reset();
      setMessage((error as Error).message);
    }
    finally { setBusy(false); }
  };

  if (order?.status === 'paid') return <p className="tv-checkout-success" role="status"><CheckCircle2 size={17} /> Đã xác nhận thanh toán</p>;
  const pending = order && ['pending', 'pending_payment'].includes(order.status);
  const checkoutUrl = order?.payment?.checkout_url;
  const hasPayment = Boolean(order?.payment || order?.mock_mode);
  const canStartSimulation = simulationEnabled && !orderPath;
  const waitingForOrder = Boolean(orderPath && !order);
  return <section className="tv-checkout" aria-label="Thanh toán vé tour">
    <h3><CreditCard size={19} /> Vé trọn tuyến · {formatVnd(price)}</h3>
    {canStartSimulation && <div className="tv-checkout-test">
      <p><FlaskConical size={16} /> Chế độ thử nghiệm · Không chuyển tiền thật</p>
      <button type="button" className="tv-btn-action-primary" disabled={busy} onClick={() => void check(true)}>
        {busy ? 'Đang xác nhận…' : 'Mô phỏng thanh toán thành công'}
      </button>
    </div>}
    {waitingForOrder && <div className="tv-payment">
      <p role="status">Đang kiểm tra đơn đã lưu…</p>
      <button type="button" className="tv-btn-action-secondary" disabled={busy} onClick={() => void check()}>Kiểm tra thanh toán</button>
    </div>}
    {!canStartSimulation && !waitingForOrder && (!order || pending && !hasPayment) && <form className="tv-checkout-form" onSubmit={submit}>
      <label>Họ và tên<input required maxLength={150} autoComplete="name" value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Số điện thoại<input type="tel" required minLength={8} maxLength={20} autoComplete="tel" value={phone} onChange={e => setPhone(e.target.value)} /></label>
      <label>Phương thức<select value={method} onChange={e => setMethod(e.target.value as 'vietqr' | 'visa')}>
        <option value="vietqr">Chuyển khoản VietQR</option><option value="visa">Thẻ qua VNPAY</option>
      </select></label>
      <button className="tv-btn-action-primary" disabled={busy}>{busy ? 'Đang xử lý…' : pending ? 'Mở lại thanh toán' : 'Tạo đơn thanh toán'}</button>
    </form>}
    {pending && <div className="tv-payment">
      <p>Đang chờ thanh toán</p>
      {order.mock_mode ? <button type="button" className="tv-btn-action-primary" disabled={busy} onClick={() => void check(true)}>Mô phỏng thanh toán thành công</button>
        : <>
          {order.payment?.qr_code_data && <QRCodeSVG value={order.payment.qr_code_data} size={172} marginSize={4} title="Mã VietQR thanh toán" />}
          {checkoutUrl && /^https:\/\//i.test(checkoutUrl) && <a className="tv-btn-action-primary" href={checkoutUrl} target="_blank" rel="noreferrer">Mở cổng thanh toán</a>}
        </>}
      <button type="button" className="tv-btn-action-secondary" disabled={busy} onClick={() => void check()}>Kiểm tra thanh toán</button>
    </div>}
    {order?.status === 'requires_review' && <p className="tv-notice">Đơn cần được đối soát. Giữ mã đơn {order.order_id} để được hỗ trợ.</p>}
    {order && !pending && order.status !== 'requires_review' && <div className="tv-payment">
      <p>Phiên thanh toán đã kết thúc.</p>
      <button type="button" className="tv-btn-action-secondary" onClick={reset}>Tạo đơn mới</button>
    </div>}
    {message && <p role="status" className="tv-notice">{message}</p>}
  </section>;
}
